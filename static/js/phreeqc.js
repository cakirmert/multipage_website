// Shared WASM-PHREEQC helper used by every page that needs a live solver.
// One module instance + one IPhreeqc handle per page is enough; PHREEQC is
// fast (single-digit ms per solve at this scale) and threading isn't needed.
//
// Usage:
//   import { getPhreeqc } from "../js/phreeqc.js";
//   const phr = await getPhreeqc();
//   const result = phr.run(`SOLUTION 1 ... SELECTED_OUTPUT 1 ... END`);
//   // result.rows is an array of {column:value} objects, last row = post-equilibration.

import createIPhreeqcModule from "../driver/iphreeqc.mjs";

let _modulePromise = null;
let _instance     = null;

/** Lazy-load the WASM module. Idempotent. */
export async function getPhreeqc({ database = "phreeqc.dat" } = {}) {
    if (!_modulePromise) {
        _modulePromise = (async () => {
            const Module = await createIPhreeqcModule({
                // Resolve .wasm/.data sidecars relative to driver/ no matter where the page is.
                locateFile: (p) => new URL("../driver/" + p, import.meta.url).href,
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
                outOn:   c("ipq_set_output_string_on", "number", ["number","number"]),
                outStr:  c("ipq_get_output_string", "string", ["number"]),
            };

            const id = ipq.create();
            ipq.errOn(id, 1);
            ipq.soOn(id,  1);
            if (ipq.loadDb(id, database) !== 0) {
                throw new Error("PHREEQC LoadDatabase failed: " + ipq.errStr(id));
            }
            return { Module, ipq, id };
        })();
    }
    if (!_instance) _instance = await _modulePromise;
    return wrap(_instance);
}

function readCell(inst, r, col) {
    const ptr = inst.ipq.cellPtr(inst.id, r, col);
    if (!ptr) return null;
    const s = inst.Module.UTF8ToString(ptr);
    inst.ipq.freeStr(ptr);
    return s;
}

function wrap(inst) {
    return {
        /**
         * Run a PHREEQC input string and return the SELECTED_OUTPUT 1 block as
         * { header: string[], rows: Array<Record<string, number|null>> }.
         * The last row is the result of the last simulation step.
         */
        run(input, { selectedOutputN = 1 } = {}) {
            const code = inst.ipq.runStr(inst.id, input);
            if (code !== 0) {
                throw new Error("PHREEQC RunString failed:\n" + inst.ipq.errStr(inst.id));
            }
            inst.ipq.selSet(inst.id, selectedOutputN);
            const rows = inst.ipq.selRows(inst.id);
            const cols = inst.ipq.selCols(inst.id);
            if (rows < 1) return { header: [], rows: [] };
            const header = [];
            for (let c = 0; c < cols; c++) header.push(readCell(inst, 0, c));
            const data = [];
            for (let r = 1; r < rows; r++) {
                const obj = {};
                for (let c = 0; c < cols; c++) {
                    const v = readCell(inst, r, c);
                    obj[header[c]] = v === null || v === "" ? null : Number(v);
                }
                data.push(obj);
            }
            return { header, rows: data };
        },
        /** Just the last data row (typical case after EQUILIBRIUM_PHASES). */
        runLast(input, opts) {
            const r = this.run(input, opts);
            if (!r.rows.length) throw new Error("PHREEQC produced no data rows");
            return { header: r.header, data: r.rows[r.rows.length - 1] };
        },
    };
}

/** Helper: format a number for the species table (sci notation, 4 sig figs). */
export function fmtSci(x) {
    if (x === null || x === undefined || Number.isNaN(x)) return "—";
    if (x === 0) return "0";
    return x.toExponential(4);
}

/** Helper: format a regular number, 3-4 decimal places. */
export function fmtNum(x, digits = 4) {
    if (x === null || x === undefined || Number.isNaN(x)) return "—";
    if (Math.abs(x) >= 1000 || (x !== 0 && Math.abs(x) < 0.001)) return x.toExponential(digits);
    return x.toFixed(digits);
}
