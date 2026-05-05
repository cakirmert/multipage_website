"""Precompute the DIC(TA, pCO2) grid that the original app builds at startup
(app.py:2182-2214) and dump it as JSON for the static site.  Run once.
"""
import json
from math import log10
from pathlib import Path

import phreeqpython

OUT = Path(__file__).resolve().parents[1] / "assets" / "data" / "dic_pco2.json"

TA_values = list(range(0, 51))                              # 1-50 mmol/kgw
CO2_list  = [10 ** (i / 10) for i in range(0, 61)]          # 1 ... 1e6 ppm

print(f"computing {len(TA_values)} x {len(CO2_list)} = {len(TA_values) * len(CO2_list)} solves")

pp = phreeqpython.PhreeqPython(database="phreeqc.dat")
grid = []
for i, TA in enumerate(TA_values):
    row = []
    for j, p in enumerate(CO2_list):
        sol = pp.add_solution({
            "units":   "mmol/kgw",
            "density": 1.000,
            "temp":    25,
            "Mg":      TA / 2,
            "Alkalinity": TA,
        })
        sol.equalize(["CO2(g)"], [log10(p * 1e-6)])
        DIC = float(sol.elements.get("C(4)", 0.0)) * 1000.0   # mol/kgw -> mmol/kgw
        row.append(DIC)
    grid.append(row)
    print(f"  TA = {TA:2d} mmol/kgw  ->  DIC range {min(row):.3e} ... {max(row):.3e}")

OUT.write_text(json.dumps({
    "TA_values": TA_values,
    "CO2_ppm":   CO2_list,
    "DIC_grid":  grid,        # rows: TA index, cols: pCO2 index, units: mmol/kgw
}))
print(f"Wrote {OUT}")
