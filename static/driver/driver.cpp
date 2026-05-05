// Thin C wrapper exposing the IPhreeqc API to JS via Emscripten.
// We expose only what the website needs: create/destroy, load db,
// run a string, query selected output, fetch errors.
#include <emscripten.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <math.h>
#include "IPhreeqc.h"

extern "C" {

EMSCRIPTEN_KEEPALIVE int  ipq_create(void)                                 { return CreateIPhreeqc(); }
EMSCRIPTEN_KEEPALIVE int  ipq_destroy(int id)                              { return DestroyIPhreeqc(id); }
EMSCRIPTEN_KEEPALIVE int  ipq_load_database(int id, const char* fn)        { return LoadDatabase(id, fn); }
EMSCRIPTEN_KEEPALIVE int  ipq_load_database_string(int id, const char* s)  { return LoadDatabaseString(id, s); }
EMSCRIPTEN_KEEPALIVE int  ipq_run_string(int id, const char* s)            { return RunString(id, s); }

EMSCRIPTEN_KEEPALIVE int  ipq_get_selected_output_count(int id)            { return GetSelectedOutputCount(id); }
EMSCRIPTEN_KEEPALIVE int  ipq_set_current_selected_output_user_number(int id, int n)
                                                                            { return SetCurrentSelectedOutputUserNumber(id, n); }
EMSCRIPTEN_KEEPALIVE int  ipq_get_selected_output_row_count(int id)        { return GetSelectedOutputRowCount(id); }
EMSCRIPTEN_KEEPALIVE int  ipq_get_selected_output_column_count(int id)     { return GetSelectedOutputColumnCount(id); }
EMSCRIPTEN_KEEPALIVE const char* ipq_get_selected_output_string(int id)    { return GetSelectedOutputString(id); }
EMSCRIPTEN_KEEPALIVE int  ipq_set_selected_output_string_on(int id, int v) { return SetSelectedOutputStringOn(id, v); }
EMSCRIPTEN_KEEPALIVE int  ipq_set_output_string_on(int id, int v)          { return SetOutputStringOn(id, v); }
EMSCRIPTEN_KEEPALIVE const char* ipq_get_output_string(int id)             { return GetOutputString(id); }

EMSCRIPTEN_KEEPALIVE int  ipq_set_error_string_on(int id, int v)           { return SetErrorStringOn(id, v); }
EMSCRIPTEN_KEEPALIVE const char* ipq_get_error_string(int id)              { return GetErrorString(id); }

EMSCRIPTEN_KEEPALIVE const char* ipq_get_selected_output_string_line(int id, int n)
                                                                            { return GetSelectedOutputStringLine(id, n); }
EMSCRIPTEN_KEEPALIVE int  ipq_get_selected_output_string_line_count(int id)
                                                                            { return GetSelectedOutputStringLineCount(id); }
// Per-cell value, double output. Writes into out_value (a host double*).
// Returns IPQ_RESULT.
EMSCRIPTEN_KEEPALIVE int  ipq_get_selected_output_double(int id, int row, int col, double* out_value) {
    VAR v;  VarInit(&v);
    int r = GetSelectedOutputValue(id, row, col, &v);
    if (r == IPQ_OK) {
        if (v.type == TT_DOUBLE)      *out_value = v.dVal;
        else if (v.type == TT_LONG)   *out_value = (double)v.lVal;
        else                          *out_value = NAN;
    }
    VarClear(&v);
    return r;
}
// Per-cell string output. Returns a pointer to a heap-allocated UTF-8 string the caller must free with ipq_free_string,
// or NULL on error / non-string type.
EMSCRIPTEN_KEEPALIVE char* ipq_get_selected_output_string_cell(int id, int row, int col) {
    VAR v;  VarInit(&v);
    int r = GetSelectedOutputValue(id, row, col, &v);
    char* out = nullptr;
    if (r == IPQ_OK) {
        if (v.type == TT_STRING && v.sVal) {
            size_t n = strlen(v.sVal) + 1;
            out = (char*)malloc(n);
            if (out) memcpy(out, v.sVal, n);
        } else if (v.type == TT_DOUBLE) {
            out = (char*)malloc(64);
            if (out) snprintf(out, 64, "%.17g", v.dVal);
        } else if (v.type == TT_LONG) {
            out = (char*)malloc(32);
            if (out) snprintf(out, 32, "%ld", v.lVal);
        }
    }
    VarClear(&v);
    return out;
}
EMSCRIPTEN_KEEPALIVE void ipq_free_string(char* p) { free(p); }

}  // extern "C"
