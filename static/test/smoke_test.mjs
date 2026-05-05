// Smoke test: load iphreeqc WASM under node, run a PHREEQC SOLUTION,
// pull selected_output, print the values. If this works, the browser will too.
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import createIPhreeqcModule from "../driver/iphreeqc.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const Module = await createIPhreeqcModule({
    locateFile: (p) => resolve(__dirname, "../driver", p),
});

const ipq_create        = Module.cwrap("ipq_create",        "number", []);
const ipq_destroy       = Module.cwrap("ipq_destroy",       "number", ["number"]);
const ipq_load_database = Module.cwrap("ipq_load_database", "number", ["number","string"]);
const ipq_run_string    = Module.cwrap("ipq_run_string",    "number", ["number","string"]);
const ipq_set_selected_output_string_on = Module.cwrap("ipq_set_selected_output_string_on", "number", ["number","number"]);
const ipq_get_selected_output_string    = Module.cwrap("ipq_get_selected_output_string",    "string", ["number"]);
const ipq_get_error_string              = Module.cwrap("ipq_get_error_string",              "string", ["number"]);
const ipq_set_error_string_on           = Module.cwrap("ipq_set_error_string_on",           "number", ["number","number"]);
const ipq_get_selected_output_count     = Module.cwrap("ipq_get_selected_output_count",     "number", ["number"]);
const ipq_set_current_selected_output_user_number = Module.cwrap("ipq_set_current_selected_output_user_number", "number", ["number","number"]);
const ipq_get_selected_output_row_count = Module.cwrap("ipq_get_selected_output_row_count", "number", ["number"]);
const ipq_get_selected_output_column_count = Module.cwrap("ipq_get_selected_output_column_count", "number", ["number"]);
const ipq_get_output_string             = Module.cwrap("ipq_get_output_string",             "string", ["number"]);
const ipq_set_output_string_on          = Module.cwrap("ipq_set_output_string_on",          "number", ["number","number"]);

const id = ipq_create();
console.log("created instance id =", id);

ipq_set_error_string_on(id, 1);
ipq_set_selected_output_string_on(id, 1);
ipq_set_output_string_on(id, 1);

const dbResult = ipq_load_database(id, "phreeqc.dat");
console.log("LoadDatabase ->", dbResult);
if (dbResult !== 0) {
    console.log("err:", ipq_get_error_string(id));
    process.exit(1);
}

// Mirror app.py:564–574 for the simplest case (graph view): T=20, CO2=415 ppm, TA=2500.
// Output: pH, sc (specific conductance), totals for C(4), and a few key species.
const log10pCO2 = Math.log10(415e-6);
const input = `
SOLUTION 1
    units      umol/kgw
    temp       20
    Alkalinity 2500
    Na         2500
EQUILIBRIUM_PHASES 1
    CO2(g)     ${log10pCO2}
SELECTED_OUTPUT 1
    -reset            false
    -pH               true
    -temperature      true
    -ionic_strength   true
    -totals           C(4)
    -molalities       HCO3- CO3-2 CO2 OH-
    -saturation_indices Calcite Aragonite Dolomite
END
`;

const runResult = ipq_run_string(id, input);
console.log("RunString ->", runResult);
if (runResult !== 0) {
    console.log("err:", ipq_get_error_string(id));
    process.exit(1);
}

const nSel = ipq_get_selected_output_count(id);
console.log("selected_output blocks:", nSel);
ipq_set_current_selected_output_user_number(id, 1);
const rows = ipq_get_selected_output_row_count(id);
const cols = ipq_get_selected_output_column_count(id);
console.log("rows:", rows, "cols:", cols);

// Read each cell as a string via the new helper (works for header strings + numeric data).
const ipq_get_selected_output_string_cell = Module.cwrap("ipq_get_selected_output_string_cell", "number", ["number","number","number"]);
const ipq_free_string                     = Module.cwrap("ipq_free_string",                     null,    ["number"]);

function readCell(row, col) {
    const ptr = ipq_get_selected_output_string_cell(id, row, col);
    if (!ptr) return null;
    const s = Module.UTF8ToString(ptr);
    ipq_free_string(ptr);
    return s;
}

console.log("--- selected output (cell-by-cell) ---");
for (let r = 0; r < rows; r++) {
    const cells = [];
    for (let c = 0; c < cols; c++) cells.push(readCell(r, c));
    console.log(`row ${r}:`, cells);
}

ipq_destroy(id);
console.log("done.");
