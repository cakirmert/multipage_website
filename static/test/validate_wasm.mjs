// Run every case from reference.json through WASM-PHREEQC and compare to the
// Python ground truth.  Pass if relative error < 1e-3 (0.1%) on every cell --
// looser than float64 because phreeqpython and our build may use slightly
// different phreeqc.dat tweaks or solver tolerances.
//
// Run with:  node validate_wasm.mjs
// (uses the bundled emsdk node so the .data sidecar is found)

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import createIPhreeqcModule from "../driver/iphreeqc.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));

// Force the Module to look for the .data sidecar next to iphreeqc.js, not the test dir.
const Module = await createIPhreeqcModule({
    locateFile: (p) => resolve(__dirname, "../driver", p),
});

const c = (name, ret, args) => Module.cwrap(name, ret, args);
const ipq_create  = c("ipq_create",  "number", []);
const ipq_destroy = c("ipq_destroy", "number", ["number"]);
const ipq_load_db = c("ipq_load_database", "number", ["number","string"]);
const ipq_run     = c("ipq_run_string", "number", ["number","string"]);
const ipq_n_so    = c("ipq_get_selected_output_count", "number", ["number"]);
const ipq_set_so  = c("ipq_set_current_selected_output_user_number", "number", ["number","number"]);
const ipq_rows    = c("ipq_get_selected_output_row_count", "number", ["number"]);
const ipq_cols    = c("ipq_get_selected_output_column_count", "number", ["number"]);
const ipq_so_on   = c("ipq_set_selected_output_string_on", "number", ["number","number"]);
const ipq_err_on  = c("ipq_set_error_string_on", "number", ["number","number"]);
const ipq_err     = c("ipq_get_error_string", "string", ["number"]);
const ipq_cell_str    = c("ipq_get_selected_output_string_cell", "number", ["number","number","number"]);
const ipq_free_string = c("ipq_free_string",                     null,    ["number"]);

function readCell(id, row, col) {
    const ptr = ipq_cell_str(id, row, col);
    if (!ptr) return null;
    const s = Module.UTF8ToString(ptr);
    ipq_free_string(ptr);
    return s;
}

function runCase(temp, pCO2_ppm, TA_umol) {
    const id = ipq_create();
    ipq_err_on(id, 1);
    ipq_so_on(id, 1);
    if (ipq_load_db(id, "phreeqc.dat") !== 0) {
        const err = ipq_err(id);
        ipq_destroy(id);
        throw new Error(`LoadDatabase failed: ${err}`);
    }

    const log10pCO2 = Math.log10(pCO2_ppm * 1e-6);
    const input = `
SOLUTION 1
    units      umol/kgw
    temp       ${temp}
    Alkalinity ${TA_umol}
    Na         ${TA_umol}
EQUILIBRIUM_PHASES 1
    CO2(g)     ${log10pCO2}
SELECTED_OUTPUT 1
    -reset            false
    -pH               true
    -temperature      true
    -ionic_strength   true
    -totals           C(4)
    -molalities       HCO3- CO3-2 CO2 H+ OH-
USER_PUNCH 1
    -headings SC
    10 PUNCH SC
END
`;
    if (ipq_run(id, input) !== 0) {
        const err = ipq_err(id);
        ipq_destroy(id);
        throw new Error(`RunString failed: ${err}`);
    }
    if (ipq_n_so(id) < 1) { ipq_destroy(id); throw new Error("no selected output"); }
    ipq_set_so(id, 1);
    const rows = ipq_rows(id), cols = ipq_cols(id);
    if (rows < 2) { ipq_destroy(id); throw new Error(`expected >=2 rows, got ${rows}`); }

    // Row 0 is the header, then one row per simulation step.
    // We want the LAST data row (after EQUILIBRIUM_PHASES kicks in).
    const header = [];
    for (let c = 0; c < cols; c++) header.push(readCell(id, 0, c));
    const last = rows - 1;
    const data = {};
    for (let cIdx = 0; cIdx < cols; cIdx++) {
        const v = readCell(id, last, cIdx);
        data[header[cIdx]] = v === null ? null : Number(v);
    }
    ipq_destroy(id);

    return {
        pH:   data["pH"],
        sc:   data["SC"],
        // C(4) total reads as "C(4)(mol/kgw)" in selected output headers.
        C4_total: data["C(4)(mol/kgw)"],
        species: {
            "HCO3-": data["m_HCO3-(mol/kgw)"] ?? 0,
            "CO3-2": data["m_CO3-2(mol/kgw)"] ?? 0,
            "CO2":   data["m_CO2(mol/kgw)"]   ?? 0,
            "H+":    data["m_H+(mol/kgw)"]    ?? 0,
            "OH-":   data["m_OH-(mol/kgw)"]   ?? 0,
        },
        _raw_header: header,
        _raw_data: data,
    };
}

function relErr(a, b) {
    if (a === 0 && b === 0) return 0;
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
const results = [];

for (const tc of ref.cases) {
    const { temp_C, pCO2_ppm, TA_umol_per_kgw } = tc.inputs;
    let actual;
    try {
        actual = runCase(temp_C, pCO2_ppm, TA_umol_per_kgw);
    } catch (e) {
        results.push({ name: tc.name, ok: false, err: e.message });
        continue;
    }

    const checks = [];
    const compare = (label, exp, got) => {
        const e = relErr(exp, got);
        checks.push({ label, exp, got, relErr: e, ok: e <= TOL });
    };

    compare("pH",       tc.expected.pH,       actual.pH);
    compare("sc",       tc.expected.sc,       actual.sc);
    compare("C(4) tot", tc.expected.C4_total, actual.C4_total);
    for (const sp of Object.keys(tc.expected.species)) {
        compare(`species[${sp}]`, tc.expected.species[sp], actual.species[sp]);
    }
    const ok = checks.every(c => c.ok);
    results.push({ name: tc.name, ok, checks, actual });
}

// Summary
let pass = 0, fail = 0;
for (const r of results) {
    if (r.ok) pass++; else fail++;
    console.log(`\n[${r.ok ? "PASS" : "FAIL"}] ${r.name}`);
    if (r.err) { console.log("  error:", r.err); continue; }
    for (const c of r.checks) {
        const tag = c.ok ? "  ok " : "  XX ";
        console.log(`${tag}${c.label.padEnd(20)} expected=${fmt(c.exp).padStart(14)}   got=${fmt(c.got).padStart(14)}   relErr=${c.relErr.toExponential(2)}`);
    }
}
console.log(`\n=== ${pass} passed, ${fail} failed (tol = ${TOL}) ===`);
process.exit(fail === 0 ? 0 : 1);
