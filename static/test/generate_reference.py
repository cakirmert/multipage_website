"""Generate ground-truth PHREEQC outputs to validate the WASM build against.

Mirrors the PHREEQC calls app.py makes ([app.py:564-588] for the Graph view, the
3-input case T/CO2/TA), but without Dash. Uses phreeqpython directly with the
default `phreeqc.dat` database -- the same database we ship into the WASM
module.

For each test case we record the same set of numbers the WASM driver pulls
through SELECTED_OUTPUT, so the two can be compared cell-by-cell.
"""
import json
from pathlib import Path
from math import log10

import phreeqpython

# Default database that ships with phreeqpython AND with our WASM bundle.
DB = "phreeqc.dat"

# Inputs lifted from app.py defaults + a few edge cases to cover the input space.
CASES = [
    # name,          T (°C), CO2 (ppm), TA (umol/kgw)
    ("default",        20.0,  415.0,  2500.0),
    ("low_ta",         20.0,  415.0,    50.0),
    ("high_ta",        20.0,  415.0, 10000.0),
    ("low_co2",        20.0,    1.0,  2500.0),
    ("high_co2",       20.0, 5000.0,  2500.0),
    ("cold",            5.0,  415.0,  2500.0),
    ("warm",           45.0,  415.0,  2500.0),
]

# Species we care about (those plotted in update_graph_2 and shown in the species table).
SPECIES = ["HCO3-", "CO3-2", "CO2", "H+", "OH-"]

# 8-input table-view test cases mirror app.py's update_graph callback.
# Each entry is a complete water composition + atmospheric CO2 partial pressure.
TABLE_CASES = [
    {
        "name": "freshwater_realistic",
        "T_C": 15.0, "pCO2_ppm": 415.0, "TA_umol_per_kgw": 2500,
        "Na": 500, "Mg": 200, "Ca": 1000, "K": 50,
        "Cl": 800, "SO4": 250, "NO3": 100, "F": 5,
    },
    {
        "name": "seawater_like",
        "T_C": 20.0, "pCO2_ppm": 415.0, "TA_umol_per_kgw": 2300,
        "Na": 469000, "Mg": 53600, "Ca": 10300, "K": 10200,
        "Cl": 546000, "SO4": 28200, "NO3": 0, "F": 70,
    },
    {
        "name": "minimal_no_cations",
        "T_C": 25.0, "pCO2_ppm": 415.0, "TA_umol_per_kgw": 1500,
        "Na": 1500, "Mg": 0, "Ca": 0, "K": 0,
        "Cl": 0, "SO4": 0, "NO3": 0, "F": 0,
    },
]


def run(temp, co2_ppm, ta_umol):
    pp = phreeqpython.PhreeqPython(database=DB)
    sol = pp.add_solution({
        "units":      "umol/kgw",
        "temp":       temp,
        "Alkalinity": ta_umol,
        "Na":         ta_umol,
    })
    sol.equalize(["CO2(g)"], [log10(co2_ppm * 1e-6)])

    # Unambiguous DIC: total moles of carbonate carbon = element C(4).
    # phreeqpython's `total("HCO3" / "CO3" / "CO2")` matches by string and is
    # ambiguous; for validation we want a quantity both sides compute the same way.
    C4_total = float(sol.elements.get("C(4)", 0.0))
    out = {
        "pH":  float(sol.pH),
        "sc":  float(sol.sc),
        "C4_total": C4_total,
        # Keep the legacy sum-of-three-totals number for reference, but don't gate on it.
        "DIC_legacy_sum": float(sol.total("CO2", units="mol")
                                + sol.total("HCO3", units="mol")
                                + sol.total("CO3", units="mol")),
        "species": {sp: float(sol.species.get(sp, 0.0)) for sp in SPECIES},
    }
    return out


def run_table(spec):
    """Mirror app.py update_graph (TABLE view, 8-input)."""
    pp = phreeqpython.PhreeqPython(database=DB)
    sol_kwargs = {
        "units":   "umol/kgw",
        "density": 1.000,
        "temp":    spec["T_C"],
        "Alkalinity": spec["TA_umol_per_kgw"],
    }
    for k_in, k_out in [("Na","Na"), ("K","K"), ("Ca","Ca"), ("Mg","Mg"),
                        ("F","F"), ("Cl","Cl"),
                        ("NO3","N(3)"), ("SO4","S")]:
        v = spec.get(k_in, 0)
        if v:
            sol_kwargs[k_out] = float(v)
    sol = pp.add_solution(sol_kwargs)
    if spec["pCO2_ppm"] > 0:
        sol.equalize(["CO2(g)"], [log10(spec["pCO2_ppm"] * 1e-6)])

    mu_val = sol.mu() if callable(sol.mu) else sol.mu
    return {
        "pH":       float(sol.pH),
        "sc":       float(sol.sc),
        "mu":       float(mu_val),
        "C4_total": float(sol.elements.get("C(4)", 0.0)),
        "Na_total": float(sol.elements.get("Na", 0.0)),
        "Ca_total": float(sol.elements.get("Ca", 0.0)),
        "species":  {sp: float(sol.species.get(sp, 0.0)) for sp in
                     ["HCO3-", "CO3-2", "CO2", "H+", "OH-",
                      "Na+", "Ca+2", "Mg+2", "K+", "Cl-", "SO4-2", "F-"]},
        "phases":   {ph: float(sol.phases.get(ph, -999.999))
                     for ph in ["Calcite", "Aragonite", "Dolomite",
                                "Gypsum", "Anhydrite", "Halite", "Fluorite"]},
    }


def main():
    cases = []
    for name, t, co2, ta in CASES:
        ref = run(t, co2, ta)
        cases.append({
            "name":   name,
            "inputs": {"temp_C": t, "pCO2_ppm": co2, "TA_umol_per_kgw": ta},
            "expected": ref,
        })
        print(f"  {name:10s}  T={t:5.1f}  CO2={co2:7.2f}  TA={ta:7.1f}"
              f" -> pH={ref['pH']:.4f}  C(4)={ref['C4_total']:.4e}  EC={ref['sc']:.2f}")

    table_cases = []
    print("\n  --- table view (8-input) ---")
    for spec in TABLE_CASES:
        ref = run_table(spec)
        table_cases.append({"name": spec["name"], "inputs": spec, "expected": ref})
        print(f"  {spec['name']:25s}  pH={ref['pH']:.4f}  C(4)={ref['C4_total']:.4e}"
              f"  EC={ref['sc']:8.2f}  SI(Calcite)={ref['phases']['Calcite']:.3f}")

    out_path = Path(__file__).parent / "reference.json"
    out_path.write_text(json.dumps({"cases": cases, "table_cases": table_cases}, indent=2))
    print(f"\nWrote {out_path} ({len(cases)} graph + {len(table_cases)} table cases)")


if __name__ == "__main__":
    main()
