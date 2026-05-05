// Validate co2sys.js against PyCO2SYS reference values.
// Looser tolerance than PHREEQC (5%) because constants are approximate by
// version; the goal is "good enough for a teaching tool", not bit-exact match.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { solveCarbonateSystem } from "../js/co2sys.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ref = JSON.parse(readFileSync(resolve(__dirname, "co2sys_reference.json"), "utf8"));

const TYPE = { 1: "TA", 2: "DIC", 3: "pH", 4: "pCO2" };
// 5% relative tolerance for derived quantities. The JS port uses Mehrbach 1973
// refit by Dickson & Millero 1987 (PyCO2SYS opt_k_carbonic=4); current PyCO2SYS
// default is Sulpis et al 2020 (opt=16). The two differ by 2-3% in pCO2/CO3.
// Both are within experimental uncertainty for ocean measurements.
const TOL  = 0.05;

function relErr(a, b) {
    if (a === 0 && b === 0) return 0;
    const denom = Math.max(Math.abs(a), Math.abs(b), 1e-300);
    return Math.abs(a - b) / denom;
}
function fmt(x) {
    if (x === null || x === undefined || Number.isNaN(x)) return "null";
    if (Math.abs(x) < 1e-3 || Math.abs(x) > 1e4) return x.toExponential(4);
    return x.toFixed(4);
}

let pass = 0, fail = 0;
for (const tc of ref.cases) {
    const i = tc.inputs;
    // Convert TA/DIC umol/kg -> mol/kg for our solver.
    const toMolKg = (t, v) => (t === "TA" || t === "DIC") ? v * 1e-6 : v;
    const t1 = TYPE[i.p1t], t2 = TYPE[i.p2t];
    const got = solveCarbonateSystem({
        par1: { type: t1, value: toMolKg(t1, i.p1v) },
        par2: { type: t2, value: toMolKg(t2, i.p2v) },
        salinity:    i.S,
        temperature: i.T,
    });

    const checks = [
        { l: "pH",    e: tc.expected.pH,    g: got.pH,             abs: 0.02 },
        { l: "TA",    e: tc.expected.TA,    g: got.TA   * 1e6,     rel: TOL },
        { l: "DIC",   e: tc.expected.DIC,   g: got.DIC  * 1e6,     rel: TOL },
        { l: "pCO2",  e: tc.expected.pCO2,  g: got.pCO2,           rel: TOL },
        { l: "HCO3",  e: tc.expected.HCO3,  g: got.HCO3 * 1e6,     rel: TOL },
        { l: "CO3",   e: tc.expected.CO3,   g: got.CO3  * 1e6,     rel: TOL },
        { l: "CO2",   e: tc.expected.CO2,   g: got.CO2  * 1e6,     rel: TOL },
        { l: "ΩCal",  e: tc.expected.OmegaCalcite,   g: got.OmegaCalcite,   rel: TOL },
        { l: "ΩAra",  e: tc.expected.OmegaAragonite, g: got.OmegaAragonite, rel: TOL },
    ];
    let ok = true;
    for (const c of checks) {
        const e = relErr(c.e, c.g);
        c.relErr = e;
        c.ok = c.abs !== undefined ? Math.abs(c.e - c.g) <= c.abs : e <= c.rel;
        if (!c.ok) ok = false;
    }
    if (ok) pass++; else fail++;
    console.log(`\n[${ok ? "PASS" : "FAIL"}] ${tc.name}  (S=${i.S}, T=${i.T})`);
    for (const c of checks) {
        const tag = c.ok ? "  ok " : "  XX ";
        const err = c.abs !== undefined ? `Δ=${(c.g - c.e).toFixed(4)}` : `relErr=${c.relErr.toExponential(2)}`;
        console.log(`${tag}${c.l.padEnd(8)} expected=${fmt(c.e).padStart(12)}  got=${fmt(c.g).padStart(12)}  ${err}`);
    }
}
console.log(`\n=== ${pass} passed, ${fail} failed ===`);
process.exit(fail === 0 ? 0 : 1);
