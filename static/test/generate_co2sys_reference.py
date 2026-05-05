"""Generate PyCO2SYS reference values for the seawater carbonate system page.
Mirrors the inputs the user could enter on the page and dumps a JSON of
expected outputs for cross-checking the JS port.
"""
import json
from pathlib import Path

import PyCO2SYS as pyco2

OUT = Path(__file__).resolve().parent / "co2sys_reference.json"

# (par1_type, par1_value, par2_type, par2_value, salinity, temperature)
# Types: 1=TA, 2=DIC, 3=pH, 4=pCO2 (PyCO2SYS convention)
CASES = [
    {"name": "default_ocean",        "p1t": 1, "p1v": 2300,  "p2t": 2, "p2v": 2000,  "S": 35, "T": 25},
    {"name": "high_pH",              "p1t": 1, "p1v": 2300,  "p2t": 3, "p2v": 8.5,   "S": 35, "T": 25},
    {"name": "low_DIC",              "p1t": 1, "p1v": 2300,  "p2t": 2, "p2v": 1500,  "S": 35, "T": 25},
    {"name": "polar_cold",           "p1t": 1, "p1v": 2350,  "p2t": 2, "p2v": 2150,  "S": 33, "T":  2},
    {"name": "tropical_warm",        "p1t": 1, "p1v": 2280,  "p2t": 2, "p2v": 1950,  "S": 36, "T": 28},
    {"name": "from_pCO2",            "p1t": 1, "p1v": 2300,  "p2t": 4, "p2v": 415,   "S": 35, "T": 25},
    {"name": "from_DIC_pH",          "p1t": 2, "p1v": 2000,  "p2t": 3, "p2v": 8.10,  "S": 35, "T": 25},
]

cases = []
for c in CASES:
    r = pyco2.sys(par1_type=c["p1t"], par1=c["p1v"],
                  par2_type=c["p2t"], par2=c["p2v"],
                  temperature=c["T"], salinity=c["S"])
    cases.append({
        "name":   c["name"],
        "inputs": c,
        "expected": {
            "TA":    float(r["alkalinity"]),                # umol/kg
            "DIC":   float(r["dic"]),
            "pH":    float(r["pH_total"]),
            "pCO2":  float(r["pCO2"]),                      # uatm
            "HCO3":  float(r["bicarbonate"]),               # umol/kg
            "CO3":   float(r["carbonate"]),
            "CO2":   float(r["CO2"]),
            "OmegaCalcite":   float(r["saturation_calcite"]),
            "OmegaAragonite": float(r["saturation_aragonite"]),
        },
    })
    print(f"  {c['name']:18s}  pH={cases[-1]['expected']['pH']:.4f}  "
          f"DIC={cases[-1]['expected']['DIC']:7.1f}  pCO2={cases[-1]['expected']['pCO2']:6.1f}  "
          f"OmegaCal={cases[-1]['expected']['OmegaCalcite']:.3f}")

OUT.write_text(json.dumps({"cases": cases}, indent=2))
print(f"\nWrote {OUT}  ({len(cases)} cases)")
