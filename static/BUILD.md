# Building WASM-PHREEQC from source

Most users don't need to rebuild — the runtime artefacts in [`driver/`](driver/)
(`iphreeqc.mjs`, `iphreeqc.wasm`, `iphreeqc.data`) are committed and the site
works out of the box. Read this only if you want to:

* upgrade to a newer IPhreeqc release,
* swap in a different `phreeqc.dat` thermodynamic database,
* port to a different solver entirely, or
* verify what's in the committed `iphreeqc.wasm` by reproducing it.

## Why the build chain is gitignored

The Emscripten SDK, the IPhreeqc source clone, and the CMake build tree
together weigh ~2 GB. None of it is needed at runtime, so all three are listed
in [`.gitignore`](.gitignore):

```
emsdk/                 # 1.6 GB — Emscripten compiler toolchain (LLVM + node + python)
iphreeqc-src/          # 68 MB  — git clone of usgs-coupled/iphreeqc
iphreeqc-build/        # 39 MB  — CMake build tree (.o files, libIPhreeqc.a, intermediate test exes)
lib/                   # empty placeholder
```

The four files we keep — `driver/iphreeqc.mjs`, `driver/iphreeqc.wasm`,
`driver/iphreeqc.data`, `driver/driver.cpp`, plus `driver/phreeqc.dat` — are
the entire shipped runtime.

## What the build does

```
┌─────────────────────────┐  emcmake     ┌─────────────────────────┐
│ iphreeqc-src/           │ ───────────▶ │ iphreeqc-build/         │
│   src/*.cpp (engine)    │              │   libIPhreeqc.a         │
│   src/phreeqcpp/*.cpp   │              │   (static WASM archive) │
└─────────────────────────┘              └────────────┬────────────┘
                                                      │
                                                      │ em++ -s MODULARIZE=1 ...
                                                      ▼
┌─────────────────────────┐              ┌─────────────────────────┐
│ driver/driver.cpp       │ ───────────▶ │ driver/iphreeqc.{mjs,   │
│   (small C ABI shim)    │              │   wasm,data}            │
└─────────────────────────┘              │   (~1.7 MB total)       │
                                         └─────────────────────────┘
```

`driver.cpp` is a thin `extern "C"` wrapper that re-exports the IPhreeqc
public API under simpler names (`ipq_create`, `ipq_load_database`,
`ipq_run_string`, …) plus a couple of helpers for reading SELECTED_OUTPUT
values cell-by-cell from JS. It's the only original C++ we ship.

## Step-by-step rebuild

Tested on Windows + Git Bash, but the commands are POSIX-portable.

### 1. Install Emscripten (no admin needed)

```sh
cd static
git clone --depth 1 https://github.com/emscripten-core/emsdk
cd emsdk
./emsdk install latest
./emsdk activate latest
cd ..
```

You'll get `emsdk/upstream/emscripten/em++.bat` (or `.sh`) and
`emsdk/upstream/emscripten/emcmake.bat`. Add them to PATH or call by absolute
path. Emscripten ships its own Node and Python; nothing else needed.

### 2. Install CMake + Ninja (no admin)

```sh
python -m pip install --user cmake ninja
```

The Python wheels install `cmake.exe` and `ninja.exe` under
`%APPDATA%\Python\PythonXY\Scripts\`. Add to PATH or use full paths.

### 3. Clone IPhreeqc source

```sh
git clone --depth 1 https://github.com/usgs-coupled/iphreeqc iphreeqc-src
```

Confirm `iphreeqc-src/CMakeLists.txt` line ~5 says `LANGUAGES CXX C` — only
C++/C are required. The Fortran in the tree (~1.6 % of LOC) is for Fortran
language bindings only and we explicitly disable it (Emscripten can't compile
Fortran).

### 4. Configure with Emscripten

```sh
mkdir iphreeqc-build && cd iphreeqc-build
emcmake cmake \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF \
  -DIPHREEQC_ENABLE_MODULE=OFF \
  -DIPHREEQC_FORTRAN_TESTING=OFF \
  ../iphreeqc-src
```

`emcmake` is Emscripten's wrapper; it injects the right toolchain file so
CMake builds for `wasm32-unknown-emscripten` instead of native.

### 5. Compile the static library

```sh
ninja
```

This produces `iphreeqc-build/libIPhreeqc.a` (~13 MB of WASM bytecode in a
static archive). It also builds Emscripten-flavoured test executables that
we don't use.

### 6. Sync the database file

This is the critical step that bit us once. `phreeqpython` ships its own
`phreeqc.dat` (1851 lines, MD5 `fca384eb…`) which differs from the IPhreeqc
master tree's version (1974 lines). They give different equilibrium
constants, so WASM output diverges from `phreeqpython` numerics if you mix
them up.

Always copy phreeqpython's file:

```sh
cp $(python -c "import phreeqpython, os; print(os.path.dirname(phreeqpython.__file__))")/database/phreeqc.dat \
   driver/phreeqc.dat
```

### 7. Link the driver into a shipping module

```sh
cd driver
em++ -O3 \
  -I ../iphreeqc-src/src \
  -I ../iphreeqc-src/src/phreeqcpp/common \
  driver.cpp \
  ../iphreeqc-build/libIPhreeqc.a \
  -o iphreeqc.mjs \
  -s MODULARIZE=1 \
  -s EXPORT_ES6=1 \
  -s EXPORT_NAME=createIPhreeqcModule \
  -s ENVIRONMENT=web,worker,node \
  -s ALLOW_MEMORY_GROWTH=1 \
  -s INITIAL_MEMORY=33554432 \
  -s STACK_SIZE=8388608 \
  -s EXPORTED_RUNTIME_METHODS='["ccall","cwrap","UTF8ToString","stringToUTF8","FS","lengthBytesUTF8"]' \
  -s EXPORTED_FUNCTIONS='["_ipq_create","_ipq_destroy","_ipq_load_database","_ipq_load_database_string","_ipq_run_string","_ipq_get_selected_output_count","_ipq_set_current_selected_output_user_number","_ipq_get_selected_output_row_count","_ipq_get_selected_output_column_count","_ipq_get_selected_output_string","_ipq_set_selected_output_string_on","_ipq_set_output_string_on","_ipq_get_output_string","_ipq_set_error_string_on","_ipq_get_error_string","_ipq_get_selected_output_string_line","_ipq_get_selected_output_string_line_count","_ipq_get_selected_output_double","_ipq_get_selected_output_string_cell","_ipq_free_string","_malloc","_free"]' \
  --preload-file phreeqc.dat
```

The flags in detail:

| Flag | Why |
|------|-----|
| `MODULARIZE=1 EXPORT_ES6=1` | Output a real `export default createIPhreeqcModule` so browsers can `import` it as an ES module. Without `EXPORT_ES6`, Emscripten emits a UMD-ish file that fails in browsers (Node accepts it via interop). |
| `EXPORT_NAME` | Function name the JS side imports. |
| `ENVIRONMENT=web,worker,node` | Generates only the env-detection paths we'll actually use. Smaller bundle. |
| `ALLOW_MEMORY_GROWTH=1` | PHREEQC's working memory varies with input size; let WASM `memory.grow` rather than picking a fixed cap. |
| `INITIAL_MEMORY` / `STACK_SIZE` | Defaults are too small for non-trivial PHREEQC runs; these are conservative starting sizes. |
| `EXPORTED_RUNTIME_METHODS` | JS-side helpers we use from `js/phreeqc.js` — `ccall`/`cwrap` to call our exported functions, `UTF8ToString` to read C strings. |
| `EXPORTED_FUNCTIONS` | Without this list, Emscripten dead-code-eliminates the C ABI exports. Every name has the underscore prefix that `extern "C"` symbols get. |
| `--preload-file phreeqc.dat` | Bakes the database into a `.data` sidecar that Emscripten mounts into a virtual filesystem at startup, so `LoadDatabase("phreeqc.dat")` works exactly as it does on a real disk. |

Output: `iphreeqc.mjs` (loader, ~70 KB), `iphreeqc.wasm` (engine, ~1.7 MB),
`iphreeqc.data` (database, ~46 KB).

### 8. Validate

```sh
cd ../test
python generate_reference.py
node validate_wasm.mjs    # must report "7 passed, 0 failed (tol = 0.001)"
node validate_table.mjs   # 2/3 pass at 1e-3, 3/3 at 5%
```

If `validate_wasm.mjs` fails on any case at the 0.1 % tolerance, double-check
step 6 — almost always it's a `phreeqc.dat` mismatch.

## What's deliberately *not* committed

| Path | Size | Why ignored |
|------|-----:|-------------|
| `emsdk/`             | 1.6 GB | Toolchain. Reinstall in step 1 above. |
| `iphreeqc-src/`      | 68 MB  | External source. Reclone in step 3. |
| `iphreeqc-build/`    | 39 MB  | Intermediate build outputs. Regenerate in step 5. |

What *is* committed:

| Path | Size | Role |
|------|-----:|------|
| `driver/driver.cpp`     | 3 KB   | Source of the C ABI shim — the only original C++ we wrote. |
| `driver/phreeqc.dat`    | 54 KB  | Thermodynamic database (copy of phreeqpython's bundled file). |
| `driver/iphreeqc.mjs`   | 70 KB  | Compiled JS loader. |
| `driver/iphreeqc.wasm`  | 1.7 MB | Compiled WASM engine. |
| `driver/iphreeqc.data`  | 46 KB  | Preloaded virtual-FS image of `phreeqc.dat`. |
| `test/*.mjs`, `test/*.py` | ~30 KB | Reference generators + validators. |
