"""Convert binary/CSV assets the original Dash app reads at startup into JSON
files we can ship as static data to the browser.  Run once after the source
assets change in ../../assets.
"""
import json, os
from pathlib import Path

import pandas as pd

ROOT     = Path(__file__).resolve().parents[2]   # multipage_website-1/
ASSETS   = ROOT / "assets"
DATASET  = ROOT / "dataset"
OUT_DIR  = Path(__file__).resolve().parents[1] / "assets" / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def export_mineral_lifetimes():
    """Lasaga 1994 mineral dissolution rates (app.py:1502)."""
    df = pd.read_excel(ASSETS / "mineral_lifetimes_lasaga_1994.xlsx", engine="openpyxl")
    # Keep only the columns the page uses + light cleanup.
    cols = [c for c in df.columns if "Unnamed" not in str(c)]
    df = df[cols].dropna(subset=["Mineral"]).reset_index(drop=True)

    out = []
    for _, r in df.iterrows():
        out.append({
            "mineral":      str(r["Mineral"]),
            "log_rate":     float(r["Log rate (mol/m²/s)"]),
            "molar_volume_cm3_per_mol": float(r["Mol. vol. (cm³/mol)"]),
        })
    (OUT_DIR / "mineral_lifetimes.json").write_text(json.dumps(out, indent=2))
    print(f"  mineral_lifetimes.json  {len(out)} minerals")


def export_periodic_table():
    """Element symbol → atomic mass map (app.py:910)."""
    df = pd.read_csv(DATASET / "Periodic Table of Elements.csv")
    out = {row.Symbol: float(row.AtomicMass) for row in df.itertuples()}
    (OUT_DIR / "elements.json").write_text(json.dumps(out, indent=2))
    print(f"  elements.json           {len(out)} elements")


def export_minerals_rruff():
    """RRUFF mineral name + IMA chemistry (app.py:909). 5K rows -> ~300KB JSON."""
    df = pd.read_csv(DATASET / "RRUFF_Export_20191025_022204.csv")
    df = df.dropna(subset=["Mineral Name", "IMA Chemistry (plain)"])
    df = df[["Mineral Name", "IMA Chemistry (plain)"]].drop_duplicates()
    out = [{"name": str(n), "formula": str(f)} for n, f in
           zip(df["Mineral Name"], df["IMA Chemistry (plain)"])]
    out.sort(key=lambda r: r["name"].lower())
    (OUT_DIR / "minerals_rruff.json").write_text(json.dumps(out))
    print(f"  minerals_rruff.json     {len(out)} minerals")


def main():
    print(f"Writing static asset JSON to {OUT_DIR}")
    export_mineral_lifetimes()
    export_periodic_table()
    export_minerals_rruff()


if __name__ == "__main__":
    main()
