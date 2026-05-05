// Validate the 8-input Table-view PHREEQC call against the Python reference,
// using the exact SOLUTION block our open-carbonate.html page emits.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import createIPhreeqcModule from "../driver/iphreeqc.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const Module = await createIPhreeqcModule({
    locateFile: (p) => resolve(__dirname, "../driver", p),
});

const c = (n, ret, args) => Module.cwrap(n, ret, args);
const ipq = {
    create:  c("ipq_create",  "number", []),
    destroy: c("ipq_destroy", "number", ["number"]),
    loadDb:  c("ipq_load_database", "number", ["number","string"]),
    runStr:  c("ipq_run_string",    "number", ["number","string"]),
    selSet:  c("ipq_set_current_selected_output_user_number", "number", ["number","number"]),
    selRows: c("ipq_get_selected_output_row_count", "number", ["number"]),
    selCols: c("ipq_get_selected_output_column_count", "number", ["number"]),
    soOn:    c("ipq_set_selected_output_string_on", "number", ["number","number"]),
    errOn:   c("ipq_set_error_string_on", "number", ["number","number"]),
    errStr:  c("ipq_get_error_string", "string", ["number"]),
    cellPtr: c("ipq_get_selected_output_string_cell", "number", ["number","number","number"]),
    freeStr: c("ipq_free_string", null, ["number"]),
};

function readCell(id, r, col) {
    const ptr = ipq.cellPtr(id, r, col);
    if (!ptr) return null;
    const s = Module.UTF8ToString(ptr);
    ipq.freeStr(ptr);
    return s;
}

function runTable(spec) {
    const id = ipq.create();
    ipq.errOn(id, 1); ipq.soOn(id, 1);
    if (ipq.loadDb(id, "phreeqc.dat") !== 0) {
        const e = ipq.errStr(id); ipq.destroy(id); throw new Error(e);
    }
    const lines = [
        "SOLUTION 1",
        "    units      umol/kgw",
        "    density    1.000",
        `    temp       ${spec.T_C}`,
        ...(spec.Na  ? [`    Na         ${spec.Na}`]  : []),
        ...(spec.K   ? [`    K          ${spec.K}`]   : []),
        ...(spec.Ca  ? [`    Ca         ${spec.Ca}`]  : []),
        ...(spec.Mg  ? [`    Mg         ${spec.Mg}`]  : []),
        ...(spec.F   ? [`    F          ${spec.F}`]   : []),
        ...(spec.Cl  ? [`    Cl         ${spec.Cl}`]  : []),
        ...(spec.NO3 ? [`    N(3)       ${spec.NO3}`] : []),
        ...(spec.SO4 ? [`    S          ${spec.SO4}`] : []),
        `    Alkalinity ${spec.TA_umol_per_kgw}`,
    ];
    if (spec.pCO2_ppm > 0) {
        lines.push("EQUILIBRIUM_PHASES 1");
        lines.push(`    CO2(g)     ${Math.log10(spec.pCO2_ppm * 1e-6)}`);
    }
    lines.push(`SELECTED_OUTPUT 1
    -reset                false
    -pH                   true
    -temperature          true
    -ionic_strength       true
    -totals               C(4) Na Mg Ca K Cl S F N(3)
    -molalities           HCO3- CO3-2 CO2 H+ OH- Na+ Ca+2 Mg+2 K+ Cl- SO4-2 F-
    -saturation_indices   Calcite Aragonite Dolomite Gypsum Anhydrite Halite Fluorite
USER_PUNCH 1
    -headings SC
    10 PUNCH SC
END`);
    if (ipq.runStr(id, lines.join("\n")) !== 0) {
        const e = ipq.errStr(id); ipq.destroy(id); throw new Error(e);
    }
    ipq.selSet(id, 1);
    const rows = ipq.selRows(id), cols = ipq.selCols(id);
    const header = []; for (let c = 0; c < cols; c++) header.push(readCell(id, 0, c));
    const last = rows - 1;
    const data = {};
    for (let cIdx = 0; cIdx < cols; cIdx++) {
        const v = readCell(id, last, cIdx);
        data[header[cIdx]] = v === null || v === "" ? null : Number(v);
    }
    ipq.destroy(id);
    return data;
}

function relErr(a, b) {
    if (a === 0 && b === 0) return 0;
    if (a === null || b === null) return Number(a !== b);
    const denom = Math.max(Math.abs(a), Math.abs(b), 1e-300);
    return Math.abs(a - b) / denom;
}
function fmt(x) {
    if (x === null || x === undefined) return "null";
    if (Math.abs(x) < 1e-3 || Math.abs(x) > 1e3) return x.toExponential(4);
    return x.toFixed(4);
}

const TOL = 1e-3;
const ref = JSON.parse(readFileSync(resolve(__dirname, "reference.json"), "utf8"));

let pass = 0, fail = 0;
for (const tc of ref.table_cases) {
    let actual;
    try { actual = runTable(tc.inputs); }
    catch (e) { console.log(`[FAIL] ${tc.name}: ${e.message}`); fail++; continue; }

    const checks = [];
    const cmp = (label, exp, got) => {
        const e = relErr(exp, got);
        checks.push({ label, exp, got, e, ok: e <= TOL });
    };

    cmp("pH",       tc.expected.pH,       actual["pH"]);
    cmp("sc",       tc.expected.sc,       actual["SC"]);
    cmp("mu",       tc.expected.mu,       actual["mu"]);
    cmp("C(4) tot", tc.expected.C4_total, actual["C(4)(mol/kgw)"]);
    cmp("Na tot",   tc.expected.Na_total, actual["Na(mol/kgw)"]);
    cmp("Ca tot",   tc.expected.Ca_total, actual["Ca(mol/kgw)"]);

    const speciesMap = {
        "HCO3-": "m_HCO3-(mol/kgw)", "CO3-2": "m_CO3-2(mol/kgw)", "CO2": "m_CO2(mol/kgw)",
        "H+":    "m_H+(mol/kgw)",    "OH-":   "m_OH-(mol/kgw)",   "Na+": "m_Na+(mol/kgw)",
        "Ca+2":  "m_Ca+2(mol/kgw)",  "Mg+2":  "m_Mg+2(mol/kgw)",  "K+":  "m_K+(mol/kgw)",
        "Cl-":   "m_Cl-(mol/kgw)",   "SO4-2": "m_SO4-2(mol/kgw)", "F-":  "m_F-(mol/kgw)",
    };
    for (const [k, col] of Object.entries(speciesMap)) {
        if (k in tc.expected.species) cmp(`sp[${k}]`, tc.expected.species[k], actual[col]);
    }
    for (const ph of Object.keys(tc.expected.phases)) {
        cmp(`SI[${ph}]`, tc.expected.phases[ph], actual[`si_${ph}`]);
    }

    const ok = checks.every(c => c.ok);
    if (ok) pass++; else fail++;
    console.log(`\n[${ok ? "PASS" : "FAIL"}] ${tc.name}`);
    for (const c of checks) {
        const tag = c.ok ? "  ok " : "  XX ";
        console.log(`${tag}${c.label.padEnd(18)} expected=${fmt(c.exp).padStart(14)}  got=${fmt(c.got).padStart(14)}  relErr=${c.e.toExponential(2)}`);
    }
}
console.log(`\n=== ${pass} passed, ${fail} failed (tol = ${TOL}) ===`);
process.exit(fail === 0 ? 0 : 1);
