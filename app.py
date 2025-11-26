# -*- coding: utf-8 -*-
"""
Dash multi‑page app for “Open Carbonate System Tools”.

Heavily re‑worked by Mert, and cleaned‑up.

how the wsgi file should look like:
https://community.plotly.com/t/dash-pythonanywhere-deployment-issue/5062

"""
import os, flask, pandas as pd, phreeqpython, plotly.graph_objects as go
from dash import Dash, html, dcc, dash_table, ctx, ALL
from dash.dash_table import Format
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
from numpy import log10
from plotly.subplots import make_subplots
import numpy as np
import re
from collections import defaultdict
from dash.exceptions import PreventUpdate
from queue import Queue
from contextlib import contextmanager
import PyCO2SYS as pyco2
from pathlib import Path
# ─────────────────────────────  CONSTANTS & STYLES  ──────────────────────────
MAX_WIDTH = "1160px"   # global content width (≈ 12‑col Bootstrap container)
PAD_Y     = "2rem"     # vertical padding for header / page bottom

# ─────────────────────────────  FLASK + DASH  ────────────────────────────────
server = flask.Flask(__name__)

BOOTSWATCH = "https://cdn.jsdelivr.net/npm/bootswatch@5.3.2/dist/flatly/bootstrap.min.css"
HIGHLIGHT  = "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/monokai-sublime.min.css"
HOVER_CSS = "https://cdnjs.cloudflare.com/ajax/libs/hover.css/2.3.1/css/hover-min.css"

app = Dash(
    __name__, server=server,
    external_stylesheets=[BOOTSWATCH, HIGHLIGHT, HOVER_CSS],
    external_scripts=[],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    suppress_callback_exceptions=True,
)

app.title = "Modeling Tools for Geochemistry"

# strip Dash's default footer
#app.index_string = """<!DOCTYPE html><html lang=\"en\"><head>{%metas%}<title>{%title%}</title>{%favicon%}{%css%}</head><body>{%app_entry%}{%config%}{%scripts%}{%renderer%}</body></html>"""

# new app index string fiyx by lukas without escape quotes
app.index_string = """<!DOCTYPE html><html lang="en"><head>{%metas%}<title>{%title%}</title>{%favicon%}{%css%}</head><body>{%app_entry%}{%config%}{%scripts%}{%renderer%}</body></html>"""

# ─────────────────────────────  PATHS & HELPERS  ─────────────────────────────
BASE_DIR  = os.path.dirname(os.path.realpath(__file__))
ASSETS    = os.path.join(BASE_DIR, "assets")

def read_asset(fname: str) -> str:
    """Read UTF‑8 file from ./assets."""
    return open(os.path.join(ASSETS, fname), encoding="utf-8").read()

# Markdown / supporting text
NARRATIVE_MD  = read_asset("narrative_improved.md")
REFS_MD       = read_asset("references.md")
SOME_TEXT_MD  = read_asset("sometext.md")
INPUT_BOX_MD  = read_asset("Textbox_input.md")
OUTPUT_BOX_MD = read_asset("Textbox_output.md")
CBE_CALCULATION_MD = read_asset("CBE_calc_text.md")
REFS_CBE_MD = read_asset("references_CBE.md")

# for new apps



IMAGE_LOGO    = "/assets/uhh-logo-web.jpg"   # served by Dash `/assets` route
BACKGROUND_IMAGE = "/assets/background_image.jpg"   # served by Dash `/assets` route

# ─────────────────────────────  SHARED UI COMPONENTS  ───────────────────────

def Footer() -> html.Footer:
    """Single footer placed by every top‑level layout, pinned to bottom."""
    link_style = {"margin": "0 .8rem", "color": "white", "textDecoration": "none"}
    return html.Footer(
        dbc.Container(
            [
                html.A("Impressum",       href="/impressum",        style=link_style),
                html.A("Datenschutz",     href="/datenschutz",     style=link_style),
                html.A("Barrierefreiheit",href="/barrierefreiheit", style=link_style),
            ],
            class_name="text-center",
            style={"maxWidth": MAX_WIDTH}
        ),
        style={
            "width": "100%",
            "backgroundColor": "#333",
            "color": "white",
            "padding": "12px 0",
            "marginTop": PAD_Y,
            "marginBottom": "0",       # no gap below footer
        },
    )

def SiteHeader(title: str, crumbs: list[tuple[str, str]] | None = None) -> html.Header:
    """Renders the header with logo, title and a breadcrumb that has no bottom margin."""
    # Build a manual breadcrumb so we can zero out the <ol> margin via mb-0
    if crumbs:
        # Create <li> items
        nav_items = []
        for lbl, href in crumbs[:-1]:
            nav_items.append(
                html.Li(html.A(lbl, href=href), className="breadcrumb-item")
            )
        # Last crumb is active text
        nav_items.append(
            html.Li(crumbs[-1][0],
                    className="breadcrumb-item active",
                    **{"aria-current": "page"})
        )
        # Wrap in <nav><ol class="breadcrumb mb-0 ps-0">...
        breadcrumb = html.Nav(
            html.Ol(nav_items,
                    className="breadcrumb mb-0 ps-0",
                    style={"marginBottom": "0"}),
            **{"aria-label": "breadcrumb"},
            className="mb-0"
        )
    else:
        breadcrumb = None

    return html.Header(
        dbc.Container(
            [
                html.Img(src=IMAGE_LOGO, style={"height": "90px"}),
                html.Div(
                    breadcrumb,
                    className="align-self-end"
                )
            ],
            class_name="d-flex align-items-center",
            style={
                "maxWidth": MAX_WIDTH,
                "paddingTop": PAD_Y,
                "paddingBottom": PAD_Y,
            },
        ),
        style={"borderBottom": "1px solid #ddd"},
    )


# ─────────────────────────────  LEGAL PAGES  ────────────────────────────────

# the three markdown files were converted from the original HTML
IMPRESSUM_MD    = read_asset("imprint.md")
DATENSCHUTZ_MD  = read_asset("datenschutz.md")
BARRECHT_MD     = read_asset("barrierefreiheit.md")

def legal_layout(raw_md: str, title: str, path: str) -> html.Div:
    return html.Div([
        SiteHeader(title, [("Home", "/"), (title, path)]),
        dbc.Container(dcc.Markdown(raw_md, className="pt-3"), style={"maxWidth": MAX_WIDTH}),
        Footer(),
    ])

# ──────────────────────────────────────────────────────────────────────────────
#  CALCULATOR
# ──────────────────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────────────
#  PHREEQP SET‑UP
# ──────────────────────────────────────────────────────────────────────────────
# ────────── IPhreeqc engine pool ──────────
POOL_SIZE = min(8, max(2, 2 * (os.cpu_count() or 2)))   # tweak if you like

_pp_pool = Queue(maxsize=POOL_SIZE)
for _ in range(POOL_SIZE):
    _pp_pool.put(phreeqpython.PhreeqPython(database="vitens.dat"))

@contextmanager
def phreeqc_session():
    """Hand out one engine from the pool, put it back afterwards."""
    pp = _pp_pool.get()          # blocks if pool is empty
    try:
        yield pp
    finally:
        _pp_pool.put(pp)

# ------------------------------------------------------------------
#  1)  CSV / look‑up tables
# ------------------------------------------------------------------
filepath = os.path.split(os.path.realpath(__file__))[0]

lines = pd.read_table(
    os.path.join(filepath, "assets/bjerrum_plot_update_phreeqpython.csv"),
    sep=",", keep_default_na=False, na_filter=False, engine="python"
)
DIC_line = pd.read_table(
    os.path.join(filepath, "assets/open_carbonate_system_phreeqpython.csv"),
    sep=",", keep_default_na=False, na_filter=False, engine="python"
)
elements = pd.read_csv(
    os.path.join(filepath, "assets/Periodic Table of Elements.csv"),
    sep=",", keep_default_na=False, na_filter=False, engine="python"
)
element_weights = dict(zip(elements["Symbol"], elements["AtomicMass"]))

# ------------------------------------------------------------------
#  2)  (Molar) constants
# ------------------------------------------------------------------
M_C     = 12.011
M_CH4   = 16.04
M_CO2   = 44.01
M_CO3   = 60.01
M_H     = 1.00784
M_H2    = M_H * 2
M_H2O   = 18.01528
M_HCO3  = 61.0168
M_Na    = 22.98976928
M_NaCO3 = M_CO3 + M_Na
M_NaHCO3= M_HCO3 + M_Na
M_OH    = 17.008
M_NaOH  = M_Na + M_OH
M_O     = 15.999
M_O2    = M_O * 2
M_Mg    = 24.305
M_Ca    = 40.078
M_K     = 39.0983
M_CaCO3 = M_Ca + M_C + 3 * M_O
M_MgCO3 = M_Mg + M_C + 3 * M_O
M_MgHCO3= M_Mg + M_HCO3
M_CaHCO3= M_Ca + M_HCO3
M_CaOH  = M_Ca + M_OH
M_MgOH  = M_Mg + M_OH

# ------------------------------------------------------------------
#  3)  conversion dict  (species → g per mol)
# ------------------------------------------------------------------
conv = {
    "CH4": M_CH4, "CO2": M_CO2, "CO3-2": M_CO3, "H+": M_H, "H2": M_H2,
    "H2O": M_H2O, "HCO3-": M_HCO3, "Na+": M_Na, "NaCO3-": M_NaCO3,
    "NaHCO3": M_NaHCO3, "NaOH": M_NaOH, "O2": M_O2, "OH-": M_OH,
    "Ca+2": M_Ca, "CaCO3": M_CaCO3, "Mg+2": M_Mg, "MgCO3": M_MgCO3,
    "MgHCO3+": M_MgHCO3, "MgOH+": M_MgOH, "CaHCO3+": M_CaHCO3,
    "CaOH+": M_CaOH, "K+": element_weights["K"], "Cl-": element_weights["Cl"],
    "H2S": 2 * element_weights["H"] + element_weights["S"],
    "HS-": element_weights["H"] + element_weights["S"],
    "HSO4-": element_weights["H"] + element_weights["S"] + 4 * element_weights["O"],
    "CaHSO4+": element_weights["Ca"] + element_weights["H"] + element_weights["S"] + 4 * element_weights["O"],
    "CaSO4": element_weights["Ca"] + element_weights["S"] + 4 * element_weights["O"],
    "KSO4-": element_weights["K"] + element_weights["S"] + 4 * element_weights["O"],
    "MgSO4": element_weights["Mg"] + element_weights["S"] + 4 * element_weights["O"],
    "NaSO4-": element_weights["Na"] + element_weights["S"] + 4 * element_weights["O"],
    "S-2": element_weights["S"], "SO4-2": element_weights["S"] + 4 * element_weights["O"],
    "N2": 2 * element_weights["N"], "NH3": element_weights["N"] + 3 * element_weights["H"],
    "NH4+": element_weights["N"] + 4 * element_weights["H"], "F-": element_weights["F"],
    "NH4SO4-": element_weights["N"] + 4 * element_weights["H"] + element_weights["S"] + 4 * element_weights["O"],
    "NO2-": element_weights["N"] + 2 * element_weights["O"],
    "NO3-": element_weights["N"] + 3 * element_weights["O"],
    "HF": element_weights["H"] + element_weights["F"],
    "HF2-": element_weights["H"] + 2 * element_weights["F"],
    "MgF+": element_weights["H"] + 2 * element_weights["F"],
    "NaF": element_weights["Na"] + element_weights["F"],
}

# ------------------------------------------------------------------
#  4)  strings for DataTable columns
# ------------------------------------------------------------------
TA_s     = "TAcarb [ueq/kgw]"
T_s      = "water T [degC]"
pCO2_s   = "air pCO2 [ppm]"

Na_s  = "Na⁺ [umol/kgw]"
Mg_s  = "Mg²⁺ [umol/kgw]"
Ca_s  = "Ca²⁺ [umol/kgw]"
K_s   = "K⁺ [umol/kgw]"
Cl_s  = "Cl- [umol/kgw]"
SO4_s = "SO₄²- [umol/kgw]"
NO2_s = "NO₃⁻ [umol/kgw]"
F_s   = "F- [umol/kgw]"
PO4_s = "PO₄³⁻ [umol/kgw]"

params   = [TA_s, T_s, pCO2_s]
cations  = [Na_s, Mg_s, Ca_s, K_s]
anions   = [Cl_s, SO4_s, NO2_s, F_s]

# ------------------------------------------------------------------
#  5)  small widgets used on the “Graph” view
# ------------------------------------------------------------------
T_range = [0, 80]
T_slider = dcc.Slider(
    id="T_input", min=T_range[0], max=T_range[1], step=0.5,
    marks={x: f"{x}°C" for x in range(T_range[0], T_range[1], 10)},
    value=20, tooltip={"placement": "bottom", "always_visible": True},
    updatemode="drag",
)
CO2_value = dcc.Input(id="CO2_input", type="number", value=415,
                      placeholder="Insert CO₂ (ppm)")
alkalinity_value = dcc.Input(id="TA_input", type="number", value=2500,
                             placeholder="Insert TA")
table_composition = "table_composition"

# ───────────────────────── helper ─────────────────────────
def make_table(
    df: pd.DataFrame,
    *, id: str,
    exponent: bool = False,          # ← True ⇒ 1.23 e‑04, False ⇒ 0.000123
) -> dash_table.DataTable:
    """Return a nicely‑styled DataTable."""
    num_fmt = Format.Format(
        precision=4,
        scheme=Format.Scheme.exponent if exponent else Format.Scheme.decimal,
        trim=True,
    )
    return dash_table.DataTable(
        id=id,
        columns=[{"name": c, "id": c, "type": "numeric", "format": num_fmt}
                 for c in df.columns],
        data=df.to_dict("records"),
        editable=True,

        style_table  = {"width": "100%", "overflowX": "auto",
                        "border": "1px solid #dee2e6", "margin": "0 auto"},
        style_header = {"backgroundColor": "#f8f9fa", "fontWeight": 600,
                        "padding": "10px"},
        style_cell   = {"padding": "8px 10px", "textAlign": "right",
                        "fontSize": "1rem", "minWidth": "80px"},
        style_data_conditional=[],
    )

# ─────────────────── build blank input tables ───────────────────
basic_tbl  = make_table(                       #  ← restore “sample”
    pd.DataFrame([dict(sample=1, **{p: 0 for p in params})]),
    id="table-bulk"
)
cation_tbl = make_table(
    pd.DataFrame([dict(sample=1, **{p: 0 for p in cations})]),
    id="table-cations"
)
anion_tbl  = make_table(
    pd.DataFrame([dict(sample=1, **{p: 0 for p in anions})]),
    id="table-anions"
)

# highlight zeros in red
for tbl, cols in [(basic_tbl, params), (cation_tbl, cations), (anion_tbl, anions)]:
    tbl.style_data_conditional += [
        {"if": {"filter_query": f"{{{c}}} = 0", "column_id": c},
         "backgroundColor": "#ffe5e5", "color": "black"} for c in cols
    ]

# cards
basic_card  = dbc.Card(
    [dbc.CardHeader("Basic parameters", class_name="fw-bold"),
     dbc.CardBody(basic_tbl)], class_name="mb-4 shadow-sm")
cation_card = dbc.Card(
    [dbc.CardHeader("Cations", class_name="fw-bold"),
     dbc.CardBody(cation_tbl)], class_name="mb-4 shadow-sm")
anion_card  = dbc.Card(
    [dbc.CardHeader("Anions", class_name="fw-bold"),
     dbc.CardBody(anion_tbl)], class_name="mb-4 shadow-sm")

# ─────────────────── TABLE‑view layout ───────────────────
page1_layout = html.Div(
    [
        dbc.Container(
            [
                dcc.Markdown(NARRATIVE_MD, mathjax=True),

                dbc.Row(
                    [
                        dbc.Col(
                            dbc.Button("Table", id="btn-page-1", n_clicks=0,
                                       color="success", className="w-100",
                                       style={"fontSize": "1.3em",
                                              "backgroundColor": "#149c7d",
                                              "pointerEvents": "none"})),
                        dbc.Col(
                            dbc.Button("Graph", id="btn-page-2", n_clicks=0,
                                       color="success", className="w-100",
                                       style={"fontSize": "1.3em"})),
                    ],
                    class_name="my-4",
                ),

                # ---------------- INPUT ----------------
                html.H2("Input tables"),
                dcc.Markdown(INPUT_BOX_MD, mathjax=True),
                basic_card,
                cation_card,
                anion_card,

                # ---------------- OUTPUT ----------------
                html.H2("Output tables"),
                html.B("Resulting speciation after equilibration:"),
                html.Div(id="table1", className="my-3"),
                html.B("Saturation indices of possible minerals:"),
                html.Plaintext("Oversaturated minerals are highlighted red."),
                html.Div(id="table2", className="my-3"),
                html.B("Bulk parameters:"),
                html.Div(id="table3", className="my-3"),

                dcc.Markdown(SOME_TEXT_MD, mathjax=True, className="mt-4"),
                dcc.Markdown(REFS_MD,        mathjax=True, className="mt-4"),
            ],
            fluid=True,     # full‑width container
        ),
    ],
    style={"fontSize": "1.15em",
           "maxWidth": MAX_WIDTH,             # centre whole page
           "margin": "0 auto"},
)

# ───────────────────────────── page‑2  (GRAPH view) ─────────────────────────
page2_layout = html.Div(
    [
        dbc.Container(
            [
                dcc.Markdown(NARRATIVE_MD, mathjax=True),
                dbc.Row(
                    [
                        dbc.Col(
                            dbc.Button("Table", id="btn-page-1", n_clicks=0,
                                       color="success", className="w-100",
                                       style={"fontSize": "1.5em"}),
                        ),
                        dbc.Col(
                            dbc.Button("Graph", id="btn-page-2", n_clicks=0,
                                       color="success", className="w-100",
                                       style={"fontSize": "1.5em",
                                              "backgroundColor": "#149c7d",
                                              "pointerEvents": "none"}),
                        ),
                    ],
                    class_name="my-4",
                ),
                dbc.Row([dbc.Col("Water temperature [°C] :", md=4),
                         dbc.Col(T_slider, md=8)]),
                dbc.Row([dbc.Col("CO₂ partial pressure [ppm] :", md=4),
                         dbc.Col(CO2_value, md=8)], className="mt-2"),
                dbc.Row([dbc.Col("Total alkalinity [ueq/L] :", md=4),
                         dbc.Col(alkalinity_value, md=8)], className="mt-2"),
                dcc.Graph(id="indicator-graphic", style={"height": "150vh"}),
                html.B("Resulting speciation after the water equilibrates with the atmosphere:"),
                html.Div(id=table_composition, className="my-3"),
                dcc.Markdown(SOME_TEXT_MD, mathjax=True, className="mt-4"),
                dcc.Markdown(REFS_MD,      mathjax=True, className="mt-4"),
            ],
            fluid=True,
        )
    ],
    style={"fontSize": "1.15em",
           "maxWidth": MAX_WIDTH,             # centre whole page
           "margin": "0 auto"},
)
# ─────────────────────────────────────────────────────────────────────────────
# 8)  MAIN CALLBACKS
#     • update_graph   – builds the three result tables (TABLE view)
#     • update_graph_2 – builds the Plotly figure + species table (GRAPH view)
# ─────────────────────────────────────────────────────────────────────────────

@app.callback(
    [Output("table1", "children"),
     Output("table2", "children"),
     Output("table3", "children")],
    [Input("table-bulk",    "data"),   Input("table-bulk",    "columns"),
     Input("table-cations", "data"),   Input("table-cations", "columns"),
     Input("table-anions",  "data"),   Input("table-anions",  "columns")],
)
def update_graph(bulk_data, bulk_columns,
                 cations_data, cations_columns,
                 anions_data,  anions_columns):
    # ---------- 1 | merge the three DataTables --------------------------------
    df_bulk = pd.DataFrame(bulk_data,    columns=[c["name"] for c in bulk_columns   ]).apply(pd.to_numeric, errors="coerce")
    df_cat  = pd.DataFrame(cations_data, columns=[c["name"] for c in cations_columns]).apply(pd.to_numeric, errors="coerce")
    df_an   = pd.DataFrame(anions_data,  columns=[c["name"] for c in anions_columns ]).apply(pd.to_numeric, errors="coerce")
    df      = pd.concat([df_bulk, df_cat, df_an], axis=1)

    # ---------- 2 | run PHREEQC for the (single) row ---------------------------
    with phreeqc_session() as pp:
        inp = df.iloc[0]                                    # UI is single-row
        sol = pp.add_solution({
            "units":      "umol/kgw",
            "density":    1.000,
            "temp":       inp[T_s],
            # cations
            "Na": np.nan_to_num(inp[Na_s]),
            "K" : np.nan_to_num(inp[K_s]),
            "Ca": np.nan_to_num(inp[Ca_s]),
            "Mg": np.nan_to_num(inp[Mg_s]),
            # anions
            "F" : np.nan_to_num(inp[F_s]),
            "Cl": np.nan_to_num(inp[Cl_s]),
            "N(3)": np.nan_to_num(inp[NO2_s]),      # NO2-
            "S" : np.nan_to_num(inp[SO4_s]),        # SO4²- (vitens.dat)
            # alkalinity
            "Alkalinity": np.nan_to_num(inp[TA_s]),
        })

        pCO2 = np.nan_to_num(inp[pCO2_s])
        if pCO2 > 0:                                # open system
            pp_atm = pCO2 * 1e-6                    # ppm → atm
            sol.equalize(["CO2(g)"], [log10(pp_atm)])

    # ---------- 3 | compose the three output tables ----------------------------
    pH  = sol.pH
    SC  = sol.sc
    DIC = sol.total("CO2", units="mol") + sol.total("HCO3", units="mol") + sol.total("CO3", units="mol")

    # species
    df_sp = (pd.DataFrame.from_dict(sol.species, orient="index",
                                    columns=["concentration [mol/kgw]"])
                .reset_index().rename(columns={"index":"species"}))
    df_sp["concentration [mg/kgw]"] = {k: 1000*v*conv[k] for k,v in sol.species.items()}.values()
    df_sp["concentration [ppm]"]    = df_sp["concentration [mg/kgw]"]
    tbl1 = make_table(df_sp, id="table1-dt", exponent=True)

    # saturation indices
    df_si = (pd.DataFrame.from_dict(sol.phases, orient="index",
                                    columns=["saturation index (SI)"])
               .reset_index().rename(columns={"index":"mineral"}))
    df_si["IAP/Ksp"] = 10**df_si["saturation index (SI)"]
    tbl2 = make_table(df_si, id="table2-dt", exponent=True)
    tbl2.style_data_conditional.extend([
        {"if": {"filter_query": "{saturation index (SI)} > 0",
                "column_id": "saturation index (SI)"}, "backgroundColor":"tomato","color":"white"},
        {"if": {"filter_query": "{IAP/Ksp} > 1",
                "column_id": "IAP/Ksp"},               "backgroundColor":"tomato","color":"white"},
    ])

    # bulk numbers
    df_bulk_out = pd.DataFrame({
        "variable": ["Dissolved inorganic carbon [mol/kgw]", "pH", "EC [uS/cm]"],
        "number"  : [DIC, pH, SC],
    })
    tbl3 = make_table(df_bulk_out, id="table3-dt")

    return tbl1, tbl2, tbl3
# ─────────────────────────────────────────────────────────────────────────────
#  update_graph_2  – GRAPH view (figure + species table)
# ─────────────────────────────────────────────────────────────────────────────
@app.callback(
    [Output("indicator-graphic", "figure"),
     Output(table_composition,   "children")],
    [Input("T_input",  "value"),
     Input("CO2_input","value"),
     Input("TA_input", "value")],
)
def update_graph_2(T_input, CO2_input, TA_input):

    # ---------- 1 | sanitise numeric inputs ----------------------------------
    def _clean(x):
        if x is None:               return None
        if isinstance(x, (int,float)) : return float(x)
        try:    return float(str(x).replace(",", ""))
        except: return None

    T, CO2, TA = map(_clean, (T_input, CO2_input, TA_input))
    if None in (T, CO2, TA):
        stub  = {"data":[], "layout":{"title":"Invalid input"}}
        warn  = html.Div("Check your numbers …", style={"color":"red","fontSize":"24px"})
        return stub, warn

    # ---------- 2 | build the PHREEQC solution --------------------------------
    try:
        with phreeqc_session() as pp:
            # TA is already µeq / kgw  → use the same figure as µmol for Na and Alk
            sol = pp.add_solution({
                "units"     : "umol/kgw",
                "temp"      : T,
                "Alkalinity": TA,     # as carbonate alkalinity
                "Na"        : TA,     # monovalent counter-ion keeps charge neutral
            })

            pCO2_atm = CO2 * 1e-6                    # ppm → atm
            sol.equalize(["CO2(g)"], [log10(pCO2_atm)])
    except Exception as err:
        stub = {"data":[], "layout":{"title":"PHREEQC could not converge"}}
        warn = html.Div(str(err), style={"whiteSpace":"pre-wrap",
                                         "fontFamily":"monospace",
                                         "color":"crimson"})
        return stub, warn

    # ---------- 3 | pull numbers we’ll need ----------------------------------
    pH  = sol.pH
    SC  = sol.sc
    DIC = (sol.total("CO2",units="mol") +
           sol.total("HCO3",units="mol") +
           sol.total("CO3", units="mol"))

    # ---------- 4 | Plotly figure --------------------------------------------
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=("Inorganic carbon components<br>in the solution",
                        "DIC(T, CO₂, pH)",
                        "Fractions of DIC"),
        vertical_spacing=0.09
    )
    fig.update_layout(
        height=1200,
        title="Equilibrium solution for a pure carbonate system",
        font_family="Courier New",
        title_font_color="red",
        font_size=18,
        legend_title_font_color="green",
    )

    # (row 3) - bar chart of major species
    labels  = ["HCO<sub>3</sub><sup>-</sup>(aq)",
               "CO<sub>3</sub><sup>2-</sup>(aq)",
               "CO<sub>2</sub>(aq)",
               "H<sup>+</sup>",
               "OH<sup>-</sup>"]
    values  = [sol.total("HCO3")*1000,
               sol.total("CO3") *1000,
               sol.total("CO2") *1000,
               sol.species["H+"]*1e6,
               sol.species["OH-"]*1e6]
    fig.add_trace(go.Bar(x=labels, y=values, name="aqueous"), row=3, col=1)
    fig.update_yaxes(title_text="c [µmol L⁻¹]", row=3, col=1)

    # (row 2) - DIC reference curve + simulation point
    fig.add_trace(go.Scatter(x=DIC_line["pH"], y=DIC_line["DIC"],
                             mode="lines", name="reference 415 ppm / 25 °C"),
                  row=2, col=1)
    fig.add_trace(go.Scatter(x=[pH], y=[DIC],
                             mode="markers",
                             marker=dict(size=14, line=dict(width=2)),
                             name="solution"), row=2, col=1)
    fig.update_yaxes(title_text="DIC [mol L⁻¹]", type="log", row=2, col=1)

    # (row 1) - Bjerrum fractions
    fig.add_trace(go.Scatter(x=lines["pH"], y=lines["CO2_frac"],  name="CO₂(aq)"), row=1, col=1)
    fig.add_trace(go.Scatter(x=lines["pH"], y=lines["HCO3_frac"], name="HCO₃⁻"),   row=1, col=1)
    fig.add_trace(go.Scatter(x=lines["pH"], y=lines["CO3_frac"],  name="CO₃²⁻"),   row=1, col=1)
    fig.update_yaxes(title_text="fraction", row=1, col=1)
    fig.update_xaxes(title_text="pH",       row=1, col=1)

    # vertical guide line at system pH  (rows 1 & 2 only)
    fig.add_vline(x=pH, line_dash="dot", row=1, col=1)
    fig.add_vline(x=pH, line_dash="dot", row=2, col=1)

    # annotation block
    fig.add_annotation(
        xref="paper", yref="paper",
        x=0.02, y=0.96,
        text=f"pH = {pH:.2f}<br>DIC = {DIC:.4e} mol L⁻¹<br>EC = {SC:.1f} µS cm⁻¹",
        showarrow=False, align="left",
        bgcolor="rgba(255,255,255,0.7)"
    )

    # ---------- 5 | Species table under the plot -----------------------------
    df_sp = (pd.DataFrame.from_dict(sol.species, orient="index",
                                    columns=["concentration [mol/L]"])
               .reset_index().rename(columns={"index":"species"}))
    df_sp["concentration [mg/L]"] = {k:1000*v*conv[k] for k,v in sol.species.items()}.values()
    df_sp["concentration [ppm]"]  = df_sp["concentration [mg/L]"]

    tbl = dash_table.DataTable(
        data    = df_sp.to_dict("records"),
        columns = [{"name":c,"id":c,"type":"numeric",
                    "format":dash_table.Format.Format(precision=4,
                                                      scheme=dash_table.Format.Scheme.exponent)}
                   for c in df_sp.columns],
        style_data={"whiteSpace":"normal","height":"auto","minWidth":"100%"},
        editable=False,
        id="format_table",
    )

    return fig, tbl


# ─────────────────────────────────────────────────────────────────────────────

# ----------------------  WRAPPER for Calculator  ---------------------------

def calc_layout() -> html.Div:
    return html.Div([
        SiteHeader("Alkalinity Tool", [("Home", "/"), ("Alkalinity Tool", "/carbonate-system-modeling")]),
        html.Div(id="subpage-content", children=page1_layout),
        Footer(),
    ]
)

# toggle Table / Graph sub‑pages
@app.callback(Output("subpage-content", "children"),
              Input("btn-page-1", "n_clicks"), Input("btn-page-2", "n_clicks"))
def _toggle_pages(n1, n2):
    return page2_layout if ctx.triggered_id == "btn-page-2" else page1_layout

# ─────────────────────────────  APP LAYOUT WRAP ─────────────────────────────
app.layout = html.Div(
    [
        dcc.Location(id="url"),
        html.Div(id="page-layout", style={"flex": "1 0 auto"}),
    ],
    style={
        "display": "flex",
        "flexDirection": "column",
        "minHeight": "100vh",    # ensure full viewport
        "margin": "0",
    },
)

# ───────────────────────────────  HOME PAGE  ────────────────────────────────

def _hero_card(title: str, desc: str, href: str) -> dbc.Card:
    return dbc.Card(
        dbc.CardBody(
            [
                html.H5(title, className="card-title fw-semibold"),
                html.P(desc, className="card-text"),
                dbc.Button("Launch", href=href, color="light"),
            ],
            className="d-flex flex-column justify-content-between h-100",
        ),
        class_name="h-100 border-0 hvr-shadow",
        style={"borderRadius": "1rem", "padding": "1.5rem", "maxWidth": "340px"},
    )


# Here one must include the new applications and the sublink

def home_layout() -> html.Div:
    hero = html.Div(
        [
            html.H1(
                "Modeling Tools for Geochemistry",
                className="display-3 fw-bold text-white",
            ),
            html.P(
                "Interactive calculators for carbonate chemistry, charge-balance checking, and mineral-oxide conversions.",
                className="lead text-white mx-auto",
                style={"maxWidth": "760px"},
            ),
            dbc.Container(
                dbc.Row(
                    [
                        dbc.Col(
                            _hero_card(
                                "Open Carbonate System",
                                "Compute open-system carbonate speciation in fresh waters with table & graph views.",
                                "/carbonate-system-modeling",
                            ),
                            md=6,
                            lg=4,
                        class_name="mb-4",
                    ),
                    dbc.Col(
                        _hero_card(
                            "Seawater Carbonate System Calculator",
                            "Compute open-system carbonate speciation in seawater (PyCO2SYS)",
                            "/carbonate-system-modeling-seawater"
                            ,
                        ),
                        md=6,
                        lg=4,
                        class_name="mb-4",
                    ),
                    dbc.Col(
                        _hero_card(
                            "Charge Balance",
                            "Check major-ion analyses for electrical neutrality and flag errors over ±5 %.",
                            "/charge-balance",
                        ),
                        md=6,
                        lg=4,
                        class_name="mb-4",
                    ),
                    dbc.Col(
                        _hero_card(
                            "XRF Oxide Simulator",
                            "Convert any mineral formula into theoretical oxide weight fractions.",
                            "/xrf",
                        ),
                        md=6,
                        lg=4,
                        class_name="mb-4",
                    ),
                    dbc.Col(
                        _hero_card(
                            "Mineral Dissolution Simulation",
                            "Lifetime of a spherical crystal in water at pH=5 T=25°C",
                            "/mineral-dissolution",
                        ),
                        md=6,
                        lg=4,
                        class_name="mb-4",
                    ),
                    dbc.Col(
                        _hero_card(
                            ["Forsterite Dissolution",
                                html.Br(),
                                "f(pH, T, size)"
                                ],
                            "Forsterite dissolution model dependent on pH, temperature, and crystal radius.",
                            "/forsterite-dissolution",
                        ),
                        md=6,
                        lg=4,
                        class_name="mb-4",
                    ),
                    dbc.Col(
                        _hero_card(
                            "Bjerrum Plot Explorer",
                            "Bjerrum plots of selected organic acids and carbonic acid",
                            "/bjerrum-plot-explorer",
                        ),
                        md=6,
                        lg=4,
                        class_name="mb-4",
                    ),
                    dbc.Col(
                        _hero_card(
                            "DIC-pCO2 relationship",
                            "pCO2 and DIC relationship for diffrent TA",
                            "/dic-pCO2",
                        ),
                        md=6,
                        lg=4,
                        class_name="mb-4",
                    ),
                    ],
                class_name="g-4 justify-content-center mt-4",
                ),
            ),
        ],
        className="text-center py-5 px-3",
        style={
            "backgroundImage": "url('/assets/background_image.jpg')",
            "backgroundSize": "cover",
            "backgroundPosition": "center",
            "backgroundRepeat": "no-repeat",
            #"background": "linear-gradient(135deg,#149c7d 0%,#0d7359 100%)"
        },
    )

    return html.Div(
        [
            SiteHeader("Startseite"),
            hero,
            html.Div(style={"flex": "1 0 auto"}),
            Footer(),
        ],
        style={
            "display": "flex",
            "flexDirection": "column",
            "minHeight": "100vh",
            "margin": "0",
        },
    )


# ────────────────  X R F   mini-app  (new)  ────────────────
# ─────────────────────────────────────────────────────────────────────────────
#  pretty, read-only DataTable (zebra stripes + LOI + sub-items highlighting)
# ─────────────────────────────────────────────────────────────────────────────
def make_table2(df: pd.DataFrame, *, id: str, exponent: bool = False) -> dash_table.DataTable:
    num_fmt = Format.Format(
        precision=4,
        scheme   = Format.Scheme.exponent if exponent else Format.Scheme.decimal,
        trim     = True,
    )
    zebra = [{"if": {"row_index": "odd"}, "backgroundColor": "#fafafa"}]

    return dash_table.DataTable(
        id                     = id,
        data                   = df.to_dict("records"),
        columns                = [
            {"name": c, "id": c, "type": "numeric", "format": num_fmt}
            for c in df.columns
        ],
        editable               = False,
        sort_action            = "native",
        style_as_list_view     = True,
        style_table            = {
            "width": "100%", "overflowX": "auto",
            "border": "1px solid #dee2e6", "margin": "0 auto"
        },
        style_header           = {
            "backgroundColor": "#f8f9fa", "fontWeight": 700,
            "padding": "6px 8px"
        },
        style_cell             = {
            "padding": "4px 8px", "textAlign": "right",
            "fontSize": "0.9rem", "lineHeight": "1.2", "minWidth": "80px"
        },
        style_data_conditional = (
            zebra + [
                # LOI parent row highlight
                {"if": {"filter_query": "{Oxide} = 'LOI'"},
                 "backgroundColor": "#fff6e6", "fontWeight": 600},
                # indent the LOI name cell only
                {"if": {"filter_query": "{Oxide} = 'LOI'",
                        "column_id": "Oxide"},
                 "paddingRight": "2rem"},
                # arrow-prefixed children share LOI highlight
                {"if": {"filter_query": "{Oxide} contains '⤷'"},
                 "backgroundColor": "#fff6e6"},
                # weight sum row
                {"if": {"filter_query": "{Oxide} = 'weight sum %'"},
                 "backgroundColor": "#ffe5e5", "fontWeight": 700},
            ]
        ),
    )

# ════════════════════════════════════════════════════════════════════════════
#  X R F   mini-app
# ════════════════════════════════════════════════════════════════════════════
DATA_DIR      = os.path.join(BASE_DIR, "dataset")
minerals      = pd.read_csv(os.path.join(DATA_DIR, "RRUFF_Export_20191025_022204.csv"))
elements_tbl  = pd.read_csv(os.path.join(DATA_DIR, "Periodic Table of Elements.csv"))
ELEMENT_W     = dict(zip(elements_tbl.Symbol, elements_tbl.AtomicMass))

OXIDES: dict[str,str] = {
    "Si":"SiO2","Al":"Al2O3","Ca":"CaO","Mg":"MgO","Na":"Na2O","K":"K2O",
    "Mn":"MnO","Ti":"TiO2","Fe":"Fe2O3","P":"P2O5",
    "Ni":"NiO","Co":"CoO","Cr":"Cr2O3","Cu":"CuO","Zn":"ZnO",
    "Ag":"Ag2O","Pb":"PbO","V":"V2O5","Mo":"MoO3","W":"WO3",
    "C":"CO2","H":"H2O","S":"SO3","As":"As2O3","Sb":"Sb2O3",
}

FORMULAE = minerals["IMA Chemistry (plain)"].dropna().unique()
FORMULAE.sort()

_atom_re = re.compile(r"([A-Z][a-z]?)(\d*)")
def parse_formula(formula: str) -> dict[str,int]:
    stack, i = [defaultdict(int)], 0
    while i < len(formula):
        ch = formula[i]
        if ch.isalpha():
            m = _atom_re.match(formula, i)
            el, n = m.group(1), int(m.group(2) or 1)
            stack[-1][el] += n
            i += len(m.group(0))
        elif ch == "(":
            stack.append(defaultdict(int)); i += 1
        elif ch == ")":
            i += 1
            m   = re.match(r"(\d*)", formula[i:])
            mul = int(m.group(1) or 1)
            grp = stack.pop()
            for el0, n0 in grp.items():
                stack[-1][el0] += n0 * mul
            i += len(m.group(0))
        else:
            i += 1
    return dict(stack.pop())

def oxide_breakdown(formula: str) -> dict[str,float]:
    atoms    = parse_formula(formula)
    mol_mass = sum(ELEMENT_W[e]*n for e,n in atoms.items())
    wt = {}
    for el, n in atoms.items():
        if el not in OXIDES:
            continue
        oxide    = OXIDES[el]
        ox_atoms = parse_formula(oxide)
        ox_mass  = sum(ELEMENT_W[a]*c for a,c in ox_atoms.items())
        wt[oxide]= ox_mass * (n/ox_atoms[el]) / mol_mass * 100
    wt["LOI"]          = wt.get("H2O", 0) + wt.get("CO2", 0)
    wt["weight sum %"] = sum(wt.values()) - wt["LOI"]
    return wt


# ────────────────  X R F   option list  (NEW)  ────────────────
clean = minerals.dropna(subset=["Mineral Name", "IMA Chemistry (plain)"])

# each value is "MineralName‖Formula"  (double-pipe is an unlikely char in names)
FULL_OPTIONS: list[dict] = [
    {
        # bold name  + plain formula (unchanged visual)
        "label": html.Span(
            [html.B(row["Mineral Name"]), f" ({row['IMA Chemistry (plain)']})"]
        ),
        # unique value
        "value": f"{row['Mineral Name']}‖{row['IMA Chemistry (plain)']}",
        # search text (lower-case name + formula)
        "search": f"{row['Mineral Name']} {row['IMA Chemistry (plain)']}".lower(),
    }
    for _, row in clean.iterrows()
]

# ─────────────────────────────────────────────────────────────────────────────



def xrf_layout() -> html.Div:
    return html.Div(
        [
            # Wrap SiteHeader in a div with background
            html.Div(
                SiteHeader(
                    "XRF Mineral Oxides",
                    [("Home", "/"), ("XRF Mineral Oxides", "/xrf")],
                ),
                style={
                    "background-color": "rgba(255, 255, 255, 0.9)",  # semi-transparent white
                    "padding": "1rem 2rem",
                    "border-radius": "1rem",
                    "margin": "1rem 0",
                },
            ),

            dbc.Container(
                [
                    html.Div(
                        [
                            html.H2("Mineral Formula Selector", className="mt-4"),
                            html.P(
                                "Start typing a mineral name or its formula. "
                                "The first 50 matches are shown instantly in the dropdown.",
                                className="my-4 text-muted",
                            ),
                            dcc.Store(id="xrf-options-store", data=FULL_OPTIONS),
                            dcc.Dropdown(
                                id="xrf-formula",
                                options=FULL_OPTIONS,
                                value=FULL_OPTIONS[0]["value"],
                                searchable=True,
                                clearable=False,
                                placeholder="Start typing …",
                                style={"width": "100%"},
                                className="mb-4",
                            ),
                            dbc.Card(
                                dbc.CardBody(html.Div(id="xrf-table")),
                                class_name="shadow-sm",
                                style={"borderRadius": "1rem"},
                            ),
                        ],
                        style={
                            "background-color": "rgba(255, 255, 255, 0.9)",  # semi-transparent white
                            "padding": "2rem",
                            "border-radius": "1rem",
                        },
                    ),
                ],
                style={
                    "maxWidth": MAX_WIDTH,
                    "paddingTop": "3rem",
                    "paddingBottom": "4rem",
                },
            ),
            Footer(),
        ],
        style={
            "background-image": "url('/assets/background_image.jpg')",
            "background-size": "cover",
            "background-repeat": "no-repeat",
            "background-position": "center center",
            "min-height": "100vh",
            "width": "100%",
        }
    )



# ── super-light client-side filter (fast even on >5 000 minerals) ───────────
app.clientside_callback(
    """
    /*
       Inputs
       ------
       searchValue  – what the user is typing
       allOptions   – cached full list (in dcc.Store)
       currentValue – the item that is (or just got) selected

       Strategy
       --------
       • Never build a huge list. Show at most 300 matches.
       • If search box is empty just return the very first 300 minerals.
       • Always make sure the current selection is injected so the label
         never disappears.
       • Because *value* is only State (not Input) the callback runs ONLY
         when the user actually types, so clicking a mineral updates the
         table instantly – no heavy JS rebuild on every click.
    */
    function (searchValue, allOptions, currentValue) {
        const LIMIT = 300;                       // hard cap for speed
        if (!allOptions) { return []; }

        const needle = (searchValue || "").toLowerCase();
        const out    = [];

        for (let i = 0; i < allOptions.length && out.length < LIMIT; ++i) {
            const opt = allOptions[i];
            const text = opt.search || "";

            if (!needle || text.includes(needle)) {
                out.push(opt);
            }
        }

        // keep the chosen mineral visible, even if it’s beyond LIMIT
        if (currentValue && !out.some(o => o.value === currentValue)) {
            const keep = allOptions.find(o => o.value === currentValue);
            if (keep) { out.unshift(keep); }
        }
        return out;
    }
    """,
    Output("xrf-formula", "options"),
    Input("xrf-formula", "search_value"),        # fires only when typing
    State("xrf-options-store", "data"),          # full list stays client-side
    State("xrf-formula", "value"),               # current pick, but not a trigger
)


@app.callback(Output("xrf-table", "children"),
              Input("xrf-formula", "value"))

def _update_xrf(formula):
    if not formula:
        raise PreventUpdate

    # value is "MineralName‖Formula" – keep only the formula part
    _, formula = formula.split("‖", 1)

    wt   = oxide_breakdown(formula)
    rows = []

    # main oxides (skip H2O/CO2—they appear under LOI)
    for ox in OXIDES.values():
        if ox in ("H2O", "CO2"):
            continue
        rows.append({"Oxide": ox, "%": round(wt.get(ox, 0.0), 3)})
    # LOI + its two children, arrow-prefixed
    rows.append({"Oxide": "LOI",        "%": round(wt["LOI"],        3)})
    rows.append({"Oxide": "⤷ H2O",      "%": round(wt.get("H2O", 0.0), 3)})
    rows.append({"Oxide": "⤷ CO2",      "%": round(wt.get("CO2", 0.0), 3)})
    # weight sum
    rows.append({"Oxide": "weight sum %", "%": round(wt["weight sum %"], 3)})

    return make_table2(pd.DataFrame(rows), id="xrf-dt")


# ────────────────────────────────────────────────────────────────────────────
# 1️⃣  Seawater Carbonate System Speciation app
# ────────────────────────────────────────────────────────────────────────────
PARAMS = ['pH', 'TA', 'DIC', 'pCO2', 'Temperature']
PARAM_MAP = {'TA':1, 'DIC':2, 'pH':3, 'pCO2':4, 'Temperature':None}

def default_value_for(param: str):
    return {'TA':2000,'DIC':2000,'pH':8.10,'pCO2':420.0,'Temperature':25.0}.get(param,0)

def step_for(param: str):
    return {'TA':1,'DIC':1,'pH':0.01,'pCO2':1.0,'Temperature':0.1}.get(param,0.01)

def label_unit_for(param: str):
    return {'TA':'(µmol/kg)','DIC':'(µmol/kg)','pH':'','pCO2':'(µatm)','Temperature':'(°C)'}.get(param,'')

def make_table(df: pd.DataFrame, *, id: str, exponent: bool = False) -> dash_table.DataTable:
    num_fmt = Format.Format(precision=4, scheme=Format.Scheme.exponent if exponent else Format.Scheme.decimal, trim=True)
    return dash_table.DataTable(
        id=id,
        columns=[{"name": c, "id": c, "type": "numeric", "format": num_fmt} for c in df.columns],
        data=df.to_dict("records"),
        editable=False,
        style_table={"width": "100%", "overflowX": "auto", "margin": "0 auto"},
        style_header={"backgroundColor": "#f8f9fa","fontWeight":600,"padding":"10px"},
        style_cell={"padding":"8px 10px","textAlign":"right","fontSize":"1rem","minWidth":"80px"},
        style_data_conditional=[]
    )


def seawater_layout():
    return html.Div(
        [   # Wrap SiteHeader in a div with background
            html.Div(
                SiteHeader(
                    "Seawater Carbonate System Calculation",
                    [("Home", "/"), ("Seawater Carbonate System Calculation", "/seawater")],
                ),
                style={
                    "background-color": "rgba(255, 255, 255, 0.9)",  # semi-transparent white
                    "padding": "1rem 2rem",
                    "border-radius": "1rem",
                    "margin": "1rem 0",
                },
            ),

            # Content container
            dbc.Container(
                [
                    html.H2("Seawater Carbonate System Calculation", className="text-center my-4"),

                    html.Div(
                        [
                            html.Div([
                                html.Label("Select parameter 1"),
                                dcc.Dropdown(
                                    id='param1-dd',
                                    options=[{'label': p, 'value': p} for p in PARAMS],
                                    value='pH',
                                    clearable=False
                                )
                            ], style={'width': '32%'}),

                            html.Div([
                                html.Label("Select parameter 2"),
                                dcc.Dropdown(
                                    id='param2-dd',
                                    options=[{'label': p, 'value': p} for p in PARAMS],
                                    value='TA',
                                    clearable=False
                                )
                            ], style={'width': '32%'}),

                            html.Div([
                                html.Label("Select parameter 3"),
                                dcc.Dropdown(
                                    id='param3-dd',
                                    options=[{'label': p, 'value': p} for p in PARAMS],
                                    value='Temperature',
                                    clearable=False
                                )
                            ], style={'width': '32%'}),
                        ],
                        style={
                            'display': 'flex',
                            'gap': '2%',
                            'marginBottom': '1rem',
                            'justifyContent': 'center'
                        }
                    ),

                    html.Div(
                        id='inputs-container',
                        style={
                            'display': 'grid',
                            'gridTemplateColumns': 'repeat(3, 1fr)',
                            'gap': '1rem'
                        }
                    ),

                    html.Div(
                        [
                            dcc.Input(
                                id='salinity-input',
                                type='number',
                                value=35.0,
                                step=0.1,
                                style={'width': '120px', 'marginRight': '0.5rem'}
                            ),
                            html.Label("Salinity (PSU)")
                        ],
                        style={'marginTop': '0.75rem', 'textAlign': 'center'}
                    ),

                    html.Button(
                        'Calculate',
                        id='calculate-btn',
                        n_clicks=0,
                        style={'marginTop': '1rem'}
                    ),

                    html.Hr(),

                    html.Div(
                        id='note-container',
                        style={'color': '#666', 'marginBottom': '0.5rem'}
                    ),
                    html.Div(id='results-container')
                ],
                fluid=True,
                className="d-flex flex-column align-items-center",
                style={
                    "background-color": "rgba(255, 255, 255, 0.9)",  # semi-transparent white
                    "padding": "2rem",
                    "border-radius": "1rem",
                },
            ),

            Footer()
        ],
        style={
            'backgroundImage': 'url("/assets/seawater_2.jpg")',  # store image in assets/
            'backgroundSize': 'cover',
            'backgroundPosition': 'center',
            'minHeight': '100vh',
            'padding': '20px'
        }
    )



'''
def seawater_layout():
    return html.Div([
        SiteHeader(
            "Seawater Carbonate System Calculation",
            [("Home", "/"), ("Seawater Carbonate System Calculation", "/seawater")]
        ),

        dbc.Container([
            html.H2("Seawater Carbonate System Calculation", className="text-center my-4"),

            html.Div([
                html.Div([
                    html.Label("Select parameter 1"),
                    dcc.Dropdown(
                        id='param1-dd',
                        options=[{'label': p, 'value': p} for p in PARAMS],
                        value='pH',
                        clearable=False
                    )
                ], style={'width': '32%'}),
                html.Div([
                    html.Label("Select parameter 2"),
                    dcc.Dropdown(
                        id='param2-dd',
                        options=[{'label': p, 'value': p} for p in PARAMS],
                        value='TA',
                        clearable=False
                    )
                ], style={'width': '32%'}),
                html.Div([
                    html.Label("Select parameter 3"),
                    dcc.Dropdown(
                        id='param3-dd',
                        options=[{'label': p, 'value': p} for p in PARAMS],
                        value='Temperature',
                        clearable=False
                    )
                ], style={'width': '32%'}),
            ], style={'display': 'flex', 'gap': '2%', 'marginBottom': '1rem'}),

            html.Div(
                id='inputs-container',
                style={'display': 'grid', 'gridTemplateColumns': 'repeat(3,1fr)', 'gap': '1rem'}
            ),

            html.Div([
                dcc.Input(
                    id='salinity-input',
                    type='number',
                    value=35.0,
                    step=0.1,
                    style={'width': '120px', 'marginRight': '0.5rem'}
                ),
                html.Label("Salinity (PSU)")
            ], style={'marginTop': '0.75rem'}),

            html.Button(
                'Calculate',
                id='calculate-btn',
                n_clicks=0,
                style={'marginTop': '1rem'}
            ),
            html.Hr(),
            html.Div(
                id='note-container',
                style={'color': '#666', 'marginBottom': '0.5rem'}
            ),
            html.Div(id='results-container')
        ], fluid=True, className="d-flex flex-column align-items-center"),

        Footer(),

    ],
    style={
        'backgroundImage': 'url("/assets/waterfall.jpg")',  # store image in assets/
        'backgroundSize': 'cover',
        'backgroundPosition': 'center',
        'minHeight': '100vh',
        'padding': '20px'
        }
    )
    
'''

'''
def seawater_layout():
    return dbc.Container([
        html.H2("Seawater / Carbonate System", className="text-center my-4"),

        html.Div([
            html.Div([
                html.Label("Select parameter 1"),
                dcc.Dropdown(id='param1-dd', options=[{'label': p,'value':p} for p in PARAMS],
                             value='pH', clearable=False)
            ], style={'width':'32%'}),
            html.Div([
                html.Label("Select parameter 2"),
                dcc.Dropdown(id='param2-dd', options=[{'label': p,'value':p} for p in PARAMS],
                             value='TA', clearable=False)
            ], style={'width':'32%'}),
            html.Div([
                html.Label("Select parameter 3"),
                dcc.Dropdown(id='param3-dd', options=[{'label': p,'value':p} for p in PARAMS],
                             value='Temperature', clearable=False)
            ], style={'width':'32%'}),
        ], style={'display':'flex','gap':'2%','marginBottom':'1rem'}),

        html.Div(id='inputs-container',
                 style={'display':'grid','gridTemplateColumns':'repeat(3,1fr)','gap':'1rem'}),

        html.Div([
            dcc.Input(id='salinity-input', type='number', value=35.0, step=0.1,
                      style={'width':'120px','marginRight':'0.5rem'}),
            html.Label("Salinity (PSU)")
        ], style={'marginTop':'0.75rem'}),

        html.Button('Calculate', id='calculate-btn', n_clicks=0, style={'marginTop':'1rem'}),
        html.Hr(),
        html.Div(id='note-container', style={'color':'#666','marginBottom':'0.5rem'}),
        html.Div(id='results-container')
    ], fluid=True, className="d-flex flex-column align-items-center"),
'''

# ─────────── Render dynamic numeric inputs ───────────
@app.callback(
    Output('inputs-container','children'),
    Input('param1-dd','value'),
    Input('param2-dd','value'),
    Input('param3-dd','value')
)
def render_inputs(p1, p2, p3):
    chosen = [p1,p2,p3]
    children = []
    for p in chosen:
        children.append(html.Div([
            html.Label(f"{p} {label_unit_for(p)}"),
            dcc.Input(id={'type':'carbonate-input','param':p},
                      type='number', value=default_value_for(p), step=step_for(p),
                      style={'width':'100%'})
        ]))
    return children

# ─────────── Calculate PyCO2SYS ───────────
@app.callback(
    Output('results-container','children'),
    Output('note-container','children'),
    Input('calculate-btn','n_clicks'),
    State('param1-dd','value'),
    State('param2-dd','value'),
    State('param3-dd','value'),
    State({'type':'carbonate-input','param':ALL},'value'),
    State({'type':'carbonate-input','param':ALL},'id'),
    State('salinity-input','value'),
    prevent_initial_call=True
)
def calculate_carbonate_system(n_clicks, p1, p2, p3, values, ids, salinity):
    chosen = [p1,p2,p3]
    input_dict = {id['param']: val for id,val in zip(ids,values)}
    notes = []

    if 'Temperature' in input_dict:
        temperature = input_dict['Temperature']
    else:
        temperature = 25.0
        notes.append("Note: Temperature not selected; using 25°C")

    # Determine first two carbonate params for PyCO2SYS
    carbonate_names = [p for p in chosen if p != 'Temperature']
    if len(carbonate_names)<2:
        return html.Div([html.B("Error:"),"Please select at least two carbonate parameters"]), "; ".join(notes)
    if len(carbonate_names)>2:
        notes.append(f"Ignoring third parameter {carbonate_names[2]}")
        carbonate_names = carbonate_names[:2]

    par1_name, par2_name = carbonate_names
    par1_type, par2_type = PARAM_MAP[par1_name], PARAM_MAP[par2_name]
    par1_val, par2_val = input_dict[par1_name], input_dict[par2_name]

    try:
        results = pyco2.sys(par1_type=par1_type, par1=par1_val,
                             par2_type=par2_type, par2=par2_val,
                             temperature=temperature, salinity=salinity)

        # Separate concentration vs other parameters
        selected_vars = ["pH_total","TA","CO2","CO3","OH","Hfree","bicarbonate","carbonate","total_calcium","dic","pCO2"]
        other_vars = ["saturation_calcite","saturation_aragonite","pH"]

        filtered_results = {k:v for k,v in results.items() if k in selected_vars}
        other_results = {k:v for k,v in results.items() if k in other_vars}

        # Build tables
        table_umol = make_table(pd.DataFrame(list(filtered_results.items()), columns=["Parameter","Value (µmol/kg)"]),
                                id="table-umol")
        table_other = make_table(pd.DataFrame(list(other_results.items()), columns=["Parameter","Value"]),
                                 id="table-other")

        return html.Div([
            html.H4("Calculated Carbonate System"),
            html.H5("Concentrations"),
            table_umol,
            html.H5("Other Parameters"),
            table_other
        ]), "; ".join(notes)

    except Exception as e:
        return html.Div([html.B("Error:"), str(e)]), "; ".join(notes)


# ────────────────────────────────────────────────────────────────────────────
# 1️⃣  Mineral Crystal Sphere dissolution app
# ────────────────────────────────────────────────────────────────────────────

# Load data

#fix the data load
df_mineral = pd.read_excel(
    os.path.join(filepath, 'assets/mineral_lifetimes_lasaga_1994.xlsx'),
    engine='openpyxl')

df_mineral['MolarVolume_m3'] = df_mineral['Mol. vol. (cm³/mol)'] * 1e-6
df_mineral['Rate'] = 10 ** df_mineral['Log rate (mol/m²/s)']


equations_md = read_asset("equations_lasaga.md")
references_md = read_asset("references_lasaga.md")

def mineral_layout():
    return html.Div(
        [
            html.Div(  # centered content container
                [
                    SiteHeader(
                        "Mineral Dissolution",
                        [("Home", "/"), ("Mineral Dissolution", "/mineral-dissolution")],
                    ),

                    html.H1("Mineral Dissolution Model (rates for pH=5 T=25°C)"),
                    dcc.Markdown(equations_md, mathjax=True),

                    html.Label(
                        "Select mineral:",
                        style={
                            "fontSize": "20px",
                            "fontWeight": "bold",
                            "color": "#1a73e8",
                            "backgroundColor": "#e8f0fe",
                            "padding": "5px 10px",
                            "borderRadius": "5px",
                            "display": "inline-block",
                            "marginBottom": "10px"
                        }
                    ),
                    dcc.Dropdown(
                        id='mineral-dropdown',
                        options=[{'label': m, 'value': m} for m in df_mineral['Mineral']],
                        value=df_mineral['Mineral'].iloc[11]
                    ),

                    html.Div(
                        [
                            html.Label(
                                "Initial crystal radius (µm):",
                                style={
                                    "fontSize": "20px",
                                    "fontWeight": "bold",
                                    "color": "#1a73e8",
                                    "backgroundColor": "#e8f0fe",
                                    "padding": "5px 10px",
                                    "borderRadius": "5px",
                                    "display": "inline-block",
                                    "marginTop": "20px",  # whitespace above
                                    "marginBottom": "10px",  # whitespace below
                                }
                            ),
                            dcc.Slider(
                                id='radius-slider',
                                min=1, max=1000, step=10, value=100,
                                marks={i: f"{i} µm" for i in [1, 50, 100, 250, 500, 750, 1000]},
                                tooltip={"placement": "bottom", "always_visible": False},
                                updatemode='drag',
                                vertical=False,
                                # add margin around the slider for whitespace
                                className="my-3"  # or use style={"marginTop": "10px", "marginBottom": "20px"}
                            )
                        ],
                        style={"width": "90%", "maxWidth": "600px"}
                    ),


                    dcc.Graph(id='dissolution-plot'),

                    html.Hr(),
                    html.H2("References"),
                    dcc.Markdown(references_md),
                ],
                style={
                    "maxWidth": "1000px",
                    "margin": "0 auto",
                    "padding": "20px"
                },
            ),

            # Footer outside the centered div to span full width
            Footer(),
        ],
        style={
            "display": "flex",
            "flexDirection": "column",
            "minHeight": "100vh",
        },
    )


@app.callback(
    Output('dissolution-plot', 'figure'),
    [Input('mineral-dropdown', 'value'), Input('radius-slider', 'value')]
)

def update_plot(selected_mineral, radius_um):
    # Extract values
    row = df_mineral[df_mineral['Mineral'] == selected_mineral].iloc[0]
    R = row['Rate']
    Vm = row['MolarVolume_m3']
    r0 = radius_um * 1e-6  # µm to m

    # Time to full dissolution
    t_dissolve = r0 / (R * Vm)

    # Time array
    time = np.linspace(0, t_dissolve, 1000)
    r_t = r0 - R * Vm * time
    V_t = (4/3) * np.pi * np.clip(r_t, 0, None)**3
    n_t = V_t / Vm

    # Convert time to years
    time_years = time / (3600 * 24 * 365.25)

    # Plotly with multiple y-axes
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=time_years, y=V_t,
        name='Volume (m³)',
        yaxis='y',
        line=dict(color='blue')
    ))

    fig.add_trace(go.Scatter(
        x=time_years, y=r_t * 1e6,
        name='Radius (µm)',
        yaxis='y2',
        line=dict(color='green')
    ))

    # Add annotation for full dissolution time
    fig.add_annotation(
        text=f"Full dissolution time: {t_dissolve / (3600 * 24 * 365.25):.2f} years",
        xref="paper", yref="paper",
        x=0.05, y=0.05,  # bottom-left corner
        showarrow=False,
        font=dict(size=20, color="gray"),
        align="left",
        bordercolor="lightgray",
        borderwidth=1,
        borderpad=4,
        bgcolor="white",
        opacity=1
    )


    fig.update_layout(
        title=f"Dissolution of {selected_mineral} crystal r<sub>0</sub> ={radius_um} µm<br>resulting log dissolution rate: {np.log10(R):.3f} log10(mol/m²/s)",
        xaxis=dict(title='Time (years)',
                   exponentformat='e',  # use scientific notation like 1e+03
                   showexponent='all' ), # always show the exponent),

        yaxis=dict(
            title=dict(text='Volume (m³)', font=dict(color='blue')),
            tickfont=dict(color='blue'),
            exponentformat='e',  # use scientific notation like 1e+03
            showexponent='all'  # always show the exponent
        ),
        yaxis2=dict(
            title=dict(text='Radius (µm)', font=dict(color='green')),
            overlaying='y',
            side='right',
            tickfont=dict(color='green')
        ),


        legend=dict(x=0.7, y=0.99),
        template='simple_white'
    )



    return fig


# ────────────────────────────────────────────────────────────────────────────
# 1️⃣  Forsterite Dissolution app
# ────────────────────────────────────────────────────────────────────────────
text_forsterite = read_asset("text_forsterite.md")
references_forsterite = read_asset("references_forsterite.md")


def forsterite_dissolution_layout():
    return html.Div(
        [
            html.Div(  # centered content container
                [
                    SiteHeader(
                        "Forsterite Dissolution f(pH, T, r)",
                        [("Home", "/"), ("Forsterite Dissolution", "/forsterite-dissolution")],
                    ),

                    html.H1("Forsterite Dissolution Model"),

                    dcc.Markdown(text_forsterite,
                        mathjax=True
                    ),

                    # pH slider label and slider
                    html.Label(
                        "pH:",
                        style={
                            "fontSize": "20px",
                            "fontWeight": "bold",
                            "color": "#1a73e8",
                            "backgroundColor": "#e8f0fe",
                            "padding": "5px 10px",
                            "borderRadius": "5px",
                            "display": "inline-block",
                            "marginTop": "20px",
                            "marginBottom": "10px",
                        }
                    ),
                    dcc.Slider(
                        id='ph-slider',
                        min=0,
                        max=14,
                        step=0.1,
                        value=5,
                        marks={i: str(i) for i in range(0, 15)},
                        tooltip={"placement": "bottom", "always_visible": False},
                        updatemode='drag',
                        className="my-3",
                    ),

                    # Temperature slider label and slider
                    html.Label(
                        "Temperature (°C):",
                        style={
                            "fontSize": "20px",
                            "fontWeight": "bold",
                            "color": "#1a73e8",
                            "backgroundColor": "#e8f0fe",
                            "padding": "5px 10px",
                            "borderRadius": "5px",
                            "display": "inline-block",
                            "marginTop": "20px",
                            "marginBottom": "10px",
                        }
                    ),
                    dcc.Slider(
                        id='temp-slider',
                        min=0,
                        max=150,
                        step=1,
                        value=25,
                        marks={i: str(i) for i in range(0, 151, 20)},
                        tooltip={"placement": "bottom", "always_visible": False},
                        updatemode='drag',
                        className="my-3",
                    ),

                    # Crystal size slider (like before)
                    html.Label(
                        "Initial crystal radius (µm):",
                        style={
                            "fontSize": "20px",
                            "fontWeight": "bold",
                            "color": "#1a73e8",
                            "backgroundColor": "#e8f0fe",
                            "padding": "5px 10px",
                            "borderRadius": "5px",
                            "display": "inline-block",
                            "marginTop": "20px",
                            "marginBottom": "10px",
                        }
                    ),
                    dcc.Slider(
                        id='radius-slider',
                        min=1,
                        max=1000,
                        step=10,
                        value=100,
                        marks={i: f"{i} µm" for i in [1, 50, 100, 250, 500, 750, 1000]},
                        tooltip={"placement": "bottom", "always_visible": False},
                        updatemode='drag',
                        className="my-3",
                    ),

                    dcc.Graph(id='forsterite-dissolution-plot'),

                    html.Hr(),
                    html.H2("References"),
                    dcc.Markdown(references_forsterite),
                ],
                style={
                    "maxWidth": "1000px",
                    "margin": "0 auto",
                    "padding": "20px"
                },
            ),

            Footer(),  # full width footer outside centered container
        ],
        style={
            "display": "flex",
            "flexDirection": "column",
            "minHeight": "100vh",
        },
    )


# Placeholder callback
@app.callback(
    Output('forsterite-dissolution-plot', 'figure'),
    Input('ph-slider', 'value'),
    Input('temp-slider', 'value'),
    Input('radius-slider', 'value'),
)
def update_forsterite_plot(pH, temp, radius):

    # dissolution rates for different pH range
    def rate_low_pH(pH, T_C):
        """
        Calculate log10 of forsterite dissolution rate for pH < 5.6
        T_C: temperature in Celsius
        Returns log10(rate in mol/m²/s)
        """
        T_K = T_C + 273.15  # Convert to Kelvin
        log_rgeo = 6.05 - 0.46 * pH - (3683.0 / T_K)
        return log_rgeo

    def rate_high_pH(pH, T_C):
        """
        Calculate log10 of forsterite dissolution rate for pH > 5.6
        T_C: temperature in Celsius
        Returns log10(rate in mol/m²/s)
        """
        T_K = T_C + 273.15
        log_rgeo = 4.07 - 0.256 * pH - (3465.0 / T_K)
        return log_rgeo

    def rate_forsterite(pH, T_C):
        """
        Determine which equation to use based on pH.
        Returns log10(rate in mol/m²/s)
        """
        if pH <= 5.6:
            return rate_low_pH(pH, T_C)
        else:
            return rate_high_pH(pH, T_C)

    # Extract values
    log_rate = rate_forsterite(pH, temp)
    R = 10 ** log_rate  # Convert to mol/m²/s
    Vm = 43.79 * 1e-6
    r0 = radius * 1e-6  # µm to m

    # Time to full dissolution
    t_dissolve = r0 / (R * Vm)

    # Time array
    time = np.linspace(0, t_dissolve, 1000)
    r_t = r0 - R * Vm * time
    V_t = (4 / 3) * np.pi * np.clip(r_t, 0, None) ** 3
    n_t = V_t / Vm

    # Convert time to years
    time_years = time / (3600 * 24 * 365.25)

    # Plotly with multiple y-axes
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=time_years, y=V_t,
        name='Volume (m³)',
        yaxis='y',
        line=dict(color='blue')
    ))

    fig.add_trace(go.Scatter(
        x=time_years, y=r_t * 1e6,
        name='Radius (µm)',
        yaxis='y2',
        line=dict(color='green')
    ))

    # Add annotation for full dissolution time
    fig.add_annotation(
        text=f"Full dissolution time: {t_dissolve / (3600 * 24 * 365.25):.2f} years",
        xref="paper", yref="paper",
        x=0.05, y=0.05,  # bottom-left corner
        showarrow=False,
        font=dict(size=20, color="gray"),
        align="left",
        bordercolor="lightgray",
        borderwidth=1,
        borderpad=4,
        bgcolor="white",
        opacity=1
    )

    fig.update_layout(
        title=f" Dissolution of Forsterite crystal pH: {pH}, Temp: {temp}°C, Radius: {radius} µm<br>resulting log dissolution rate: {log_rate:.3f} log10(mol/m²/s)",
        xaxis=dict(title='Time (years)',
                   exponentformat='e',  # use scientific notation like 1e+03
                    showexponent='all'),  # always show the exponent),

        yaxis=dict(
            title=dict(text='Volume (m³)', font=dict(color='blue')),
            tickfont=dict(color='blue'),
            exponentformat='e',  # use scientific notation like 1e+03
            showexponent='all'  # always show the exponent
        ),
        yaxis2=dict(
            title=dict(text='Radius (µm)', font=dict(color='green')),
            overlaying='y',
            side='right',
            tickfont=dict(color='green')
        ),

        legend=dict(x=0.7, y=0.99),
        template='simple_white',
    )


    return fig


# ────────────────────────────────────────────────────────────────────────────
#   Bjerrum plot app
# ────────────────────────────────────────────────────────────────────────────

# resolve relative path to an absolute one
# db_path = Path.cwd() / "phreeqc_databases" / "vitens_lukas_edit.dat"
# db_path = Path.cwd() / "phreeqc_databases" / "minteq.v4_lukas_edit.dat"



# ---------- helpers ----------

def count_protons_in_master(master):
    """
    Extract total proton count from master species string, e.g. 'H3(Citrate)' -> 3.
    """
    m = re.match(r'H(\d+)\(', master)
    return int(m.group(1)) if m else 1


def count_H_in_species(species, core):
    """
    Count how many protons are explicitly attached to the acid core.

    Matches things like:
        H3(Citrate)-   -> 3
        H(Citrate)-    -> 1
        NaH(Citrate)-  -> 1   (ignore leading Na, just look at the H() group)
        Na2(Citrate)-  -> 0
        Citrate-3      -> 0
    """
    m = re.search(r'(H\d*)\(' + re.escape(core) + r'\)', species)
    if m:
        token = m.group(1)
        return 1 if token == "H" else int(token[1:])
    return 0


def group_by_protons(sol, master_species):
    """
    Build a dict {n_H: total_moles} for each protonation state.
    """
    core = master_species.split("(")[1].split(")")[0]
    sums = defaultdict(float)

    for sp, val in sol.species.items():
        if core in sp:
            nH = count_H_in_species(sp, core)
            sums[nH] += val
    return sums


def parse_acid_master(master):
    """
    Return (core, n_total_protons) for any acid string.
    - handles 'H3(Citrate)' pattern automatically

    """

    if "(" in master and ")" in master:
        core = master.split("(")[1].split(")")[0]
        m = re.match(r'H(\d+)', master)
        nH = int(m.group(1)) if m else 1
        return core, nH

    # last fallback: assume no parentheses, try a single H
    return master, 1


# ---------- main routine ----------

def calculate_bjerrum(acid_species, total_conc=1e-3, pH_range=(0, 14), step=0.1):
    pHs = np.arange(pH_range[0], pH_range[1] + step, step)
    records = []

    # Always resolve the file path relative to THIS script's location
    BASE_DIR = Path(__file__).resolve().parent
    db_path = BASE_DIR / "assets" / "phreeqc_databases" / "minteq.v4_with_fix_pH_and_corrected_CO2.dat"

    # create the engine using your custom database
    pp = phreeqpython.PhreeqPython(database=str(db_path))

    sol = pp.add_solution_simple({acid_species: total_conc},
                                 temperature=20,
                                 units='mol')

    for ph in pHs:
        sol.change_ph(ph)

        # spec = sol.species
        acid_str = acid_species
        if "(" in acid_str and ")" in acid_str:

            core, n_total = parse_acid_master(acid_species)

            # protonation groups
            group_sums = group_by_protons(sol, acid_species)
            for nH in range(n_total + 1):
                records.append({
                    "pH": ph,
                    "kind": "group",
                    "species": f"H{nH}({core})",
                    "value": group_sums.get(nH, 0.0) / total_conc
                })

        elif 'CO3' in acid_str:  # option for carbonic acid
            co2 = sol.total("CO2", units="mol")  # or "mmol" if you prefer
            hco3 = sol.total("HCO3", units="mol")
            co3 = sol.total("CO3", units="mol")

            records.append({"pH": ph, "kind": "group", "species": "CO2(aq)", "value": co2 / total_conc})
            records.append({"pH": ph, "kind": "group", "species": "HCO3-", "value": hco3 / total_conc})
            records.append({"pH": ph, "kind": "group", "species": "CO3--", "value": co3 / total_conc})

        else:
            None

    return pd.DataFrame(records)


# acid options
ACID_OPTIONS = {
    "Carbonic acid (H2CO3)": "H2CO3",  # depends on DB
    "Benzoic acid":'H(Benzoate)',
    "Acetic acid": 'H(Acetate)',
    "Citric acid": 'H3(Citrate)',
    "Formic acid": 'H(Formate)',
}


@app.callback(
    Output("bjerrum-plot", "figure"),
    Input("acid-dropdown", "value")
)


def update_bjerrum_plot(acid_species):
    df = calculate_bjerrum(acid_species)
    fig = go.Figure()
    for species in df["species"].unique():
        sub = df[df["species"] == species]
        fig.add_trace(go.Scatter(
            x=sub["pH"], y=sub["value"],
            mode="lines", name=species
        ))

    fig.update_layout(
        xaxis_title="pH",
        yaxis_title="Fraction",
        # yaxis=dict(range=[0, 1]),
        template="plotly_white"
    )
    return fig

from dash import html, dcc

# assume you already have SiteHeader and Footer components imported

def bjerrum_layout():
    return html.Div(
        [
            html.Div(
                [
                    SiteHeader(
                        "Bjerrum Plot Viewer",
                        [("Home", "/"), ("Bjerrum Plot", "/bjerrum")],
                    ),

                    html.H1("Bjerrum Plot Tool"),

                    dcc.Markdown(
                        """
                        *Use this page to explore acid speciation vs pH.*

                        Select an acid, adjust pH range, and the chart will update automatically.
                        """,
                        mathjax=True
                    ),

                    # Placeholder dropdown for acid selection
                    html.Label(
                        "Acid species:",
                        style={
                            "fontSize": "20px",
                            "fontWeight": "bold",
                            "color": "#1a73e8",
                            "backgroundColor": "#e8f0fe",
                            "padding": "5px 10px",
                            "borderRadius": "5px",
                            "display": "inline-block",
                            "marginTop": "20px",
                            "marginBottom": "10px",
                        }
                    ),
                    dcc.Dropdown(
                        id="acid-dropdown",
                        options=[
                            {"label": "Carbonic acid (H2CO3)", "value": "H2CO3"},
                            {"label": "Citric acid", "value": "H3(Citrate)"},
                            {"label": "Benzoic acid", "value": "H(Benzoate)"},
                            {"label": "Acetic acid", "value": "H(Acetate)"},
                            {"label": "Formic acid", "value": "H(Formate)"},
                        ],
                        value="H2CO3",
                        style={"width": "300px"}
                    ),

                    dcc.Graph(id="bjerrum-plot"),

                    html.Hr(),
                    html.H2("Notes"),
                    dcc.Markdown(
                        """
                        *The figure shows the calculated fraction of each protonation state as a function of pH.*
                        """
                    ),
                ],
                style={
                    "width": "90%",
                    "margin": "0 auto",
                    "padding": "20px"
                },
            ),

            Footer(),
        ],
        style={
            "display": "flex",
            "flexDirection": "column",
            "minHeight": "100vh",
        },
    )

# ────────────────────────────────────────────────────────────────────────────
#   pCO2, DIC, TA plot app
# ────────────────────────────────────────────────────────────────────────────

# create new PhreeqPython instance
pp = phreeqpython.PhreeqPython(database='vitens.dat')

# === 1) PRECOMPUTE THE GRID (your phreeqpython code) ===

TA_values = np.arange(1, 51)  # 1–50 mmol/kgw
CO2_list = [10**(i/10) for i in range(0, 61)]  # ppm

n_TA = len(TA_values)
n_CO2 = len(CO2_list)

DIC_grid = np.zeros((n_TA, n_CO2))  # Z surface: DIC(TA, pCO2)

for i, TA in enumerate(TA_values):
    for j, p in enumerate(CO2_list):

        # fresh solution for each (TA, pCO2) pair
        solution = pp.add_solution({
            "units": "mmol/kgw",
            "density": 1.000,
            "temp": 25,
            "Mg": TA / 2,
            "Alkalinity": TA
        })

        # ppm -> atm
        pCO2 = p * 1e-6

        # phreeqc uses log10(pCO2)
        input_pCO2 = np.log10(pCO2)
        solution.equalize(['CO2(g)'], [input_pCO2])

        # DIC in mmol/kgw (assuming elements['C(4)'] is mol/kgw)
        DIC_val = solution.elements['C(4)'] * 1000.0

        DIC_grid[i, j] = DIC_val





@app.callback(
    Output('dic-plot', 'figure'),
    Input('ta-slider', 'value')
)
def update_plot(selected_ta):
    # find index of selected TA
    idx = np.where(TA_values == selected_ta)[0][0]

    x = CO2_list            # pCO2 [ppm]
    y = DIC_grid[idx, :]    # DIC for this TA

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x,
        y=y,
        mode='lines',
        name="DIC"
    ))

    fig.add_trace(go.Scatter(
        x=x,
        y=[selected_ta] * len(x),
        mode='lines',
        name=f"TA = {selected_ta} mmol/kgw"
    ))

    # add vertical line for the atmopheric partial pressure

    # get full y-range dynamically
    ymin = min(y)
    ymax = max(y)

    fig.add_trace(go.Scatter(
        x=[425, 425],  # vertical line at x = 425 ppm
        y=[ymin, ymax],  # span full y range
        mode='lines',
        line=dict(color='black', width=2, dash='dash'),
        name='CO₂ = 425 ppm (atmospheric CO2 pressure)'
    ))


    fig.update_layout(
        height=1200,  # ← taller figure
        xaxis_title="pCO₂ [ppm]",
        yaxis_title="x [mmol/kgw]",
        title=f"DIC vs pCO₂ at TA = {selected_ta} mmol/kgw",
        template="plotly_white"
    )
    fig.update_xaxes(type='log') # log for the pCO2
    fig.update_yaxes(type="log")  # log y-axis  ← add this

    return fig




def dic_pco2_layout():
    return html.Div(
        [
            html.Div(
                [
                    SiteHeader(
                        "DIC vs pCO₂ Viewer",
                        [("Home", "/"), ("DIC vs pCO₂", "/dic-pco2")],
                    ),

                    html.H1("DIC vs pCO₂ for different TA levels"),

                    dcc.Markdown(
                        """
                        *Use this page to explore how dissolved inorganic carbon (DIC) 
                        varies with pCO₂ for different total alkalinity (TA) levels.*

                        Adjust the TA slider below to see how the curve changes.
                        """,
                        mathjax=True,
                    ),

                    # Slider label
                    html.Label(
                        "Total Alkalinity (TA):",
                        style={
                            "fontSize": "20px",
                            "fontWeight": "bold",
                            "color": "#1a73e8",
                            "backgroundColor": "#e8f0fe",
                            "padding": "5px 10px",
                            "borderRadius": "5px",
                            "display": "inline-block",
                            "marginTop": "20px",
                            "marginBottom": "10px",
                        },
                    ),

                    # TA slider
                    dcc.Slider(
                        id="ta-slider",
                        min=int(TA_values.min()),
                        max=int(TA_values.max()),
                        step=1,
                        value=int(TA_values.min()),  # or any default, e.g. 5
                        marks={int(t): str(int(t)) for t in TA_values[::5]},
                        tooltip={"placement": "bottom", "always_visible": True},
                    ),

                    # Main plot
                    dcc.Graph(id="dic-plot"),

                    html.Hr(),
                    html.H2("Notes"),
                    dcc.Markdown(
                        """
                        *The figure shows modelled DIC as a function of pCO₂ 
                        at the selected TA level.*
                        """
                    ),
                ],
                style={
                    "width": "90%",
                    "margin": "0 auto",
                    "padding": "20px",
                },
            ),

            Footer(),
        ],
        style={
            "display": "flex",
            "flexDirection": "column",
            "minHeight": "100vh",
        },
    )



# ────────────────────────────────────────────────────────────────────────────
# 1️⃣  Charge-Balance mini-app                                                  
# ────────────────────────────────────────────────────────────────────────────

LABEL_WIDTH = "160px"   # fixed room for the ion label
UNIT_WIDTH  = "60px"    # fixed room for the unit suffix

def ion_row(label: str, ion_id: str, default: float, unit_suffix: str) -> dbc.Row:
    return dbc.Row(
        dbc.Col(
            dbc.InputGroup(
                [
                    dbc.InputGroupText(
                        label,
                        style={"width": LABEL_WIDTH, "justifyContent": "right"},
                    ),
                    dbc.Button("-", id=f"dec-{ion_id}", color="secondary", n_clicks=0),
                    dbc.Input(
                        id=ion_id,
                        type="text",  #check if text type also works because of red outline issue
                        value=default,
                        step=0.5,
                        min=0,
                        max=2000,
                        inputMode="decimal",   # try to fix decimal problem
                        style={"textAlign": "right", "width": "110px"},
                    ),
                    dbc.Button("+", id=f"inc-{ion_id}", color="secondary", n_clicks=0),
                    dbc.InputGroupText(
                        unit_suffix,
                        style={"width": UNIT_WIDTH, "justifyContent": "center"},
                    ),
                ],
                class_name="w-100 flex-nowrap",
            ),
            md=12,
        ),
        class_name="my-2",
    )

# ───────── main layout ─────────

def cb_layout() -> html.Div:
    header = SiteHeader(
        "Charge Balance Calculator",
        [("Home", "/"), ("Charge Balance", "/charge-balance")],
    )

    # ── Intro (concise) ───────────────────────────────────────────────
    intro = html.Div(
        [
            html.H2("Charge-Balance Calculator", className="fw-bold"),
            dcc.Markdown(CBE_CALCULATION_MD, mathjax=True),
        ],
        className="text-center mb-4",
        style={"maxWidth": "760px", "margin": "0 auto"},
    )

    # ────────────────────────────────────────────────────────────────

    # neat button-style radio switch  ─────────────────────────────────────────
    unit_radio = dbc.RadioItems(
        id="cb-unit",
        options=[
            {"label": "mmol / kg", "value": "mmol/kg"},
            {"label": "mmol / L",  "value": "mmol/L"},
        ],
        value="mmol/kg",
        inline=True,
        # make each option look like a Bootstrap button
        inputClassName="btn-check",
        labelClassName="btn btn-outline-secondary",
        labelCheckedClassName="btn btn-secondary active",
        # keep both buttons in one rounded pill
        class_name="btn-group",
        style={"borderRadius": "0.5rem"},
    )

    density_grp = dbc.InputGroup([
        dbc.InputGroupText("Density"),
        dbc.Input(id="cb-density", type="number", value=1.025, step=0.001, min=0.8, max=1.3),
        dbc.InputGroupText("kg · L⁻¹"),
    ], class_name="w-100")

    inputs_card = dbc.Card(
        dbc.CardBody([
            html.H5("Measurement units", className="fw-semibold"), unit_radio,
            html.Div(id="cb-density-div", children=density_grp, className="mt-2"),
            html.P("Enter major-ion concentrations and tweak with ± buttons. The calculator recomputes instantly.",
                   className="text-muted small mt-2"),
            html.Hr(),
            html.H5("Cations", className="fw-semibold mt-2"),
            ion_row("Mg²⁺", "cb-mg", 53.6, "mmol"),
            ion_row("Ca²⁺", "cb-ca", 10.3, "mmol"),
            ion_row("Na⁺",  "cb-na", 469, "mmol"),
            ion_row("K⁺",   "cb-k",  10.2,  "mmol"),
            html.H5("Anions", className="fw-semibold mt-4"),
            ion_row("Total Alkalinity (TA)", "cb-ta", 2.3, "meq"),
            ion_row("Cl⁻",  "cb-cl", 546, "mmol"),
            ion_row("SO₄²⁻","cb-so4", 28.2, "mmol"),
            ion_row("NO₃⁻", "cb-no3", 0,   "mmol"),
        ]),
        class_name="shadow-sm h-100",
        style={"borderRadius": "1rem"},
    )

    # tiny result DataTable
    res_table = dash_table.DataTable(
        id="cb-table",
        data=[{"Metric": "Absolute CBE (eq)", "Value": 0.0}, {"Metric": "Relative CBE (%)", "Value": 0.0}],
        columns=[{"name": c, "id": c} for c in ["Metric", "Value"]],
        style_cell={"padding": "4px 8px", "textAlign": "right"},
        style_header={"display": "none"},
        style_data_conditional=[
            {"if": {"filter_query": "{Metric} = 'Relative CBE (%)' && {Value} > 5"},
             "backgroundColor": "tomato", "color": "white"},
        ],
    )

    # ── Results card (clean badges instead of a tiny table) ──────────────────────
    results_card = dbc.Card(
        dbc.CardBody(
            [
                html.H5("Results", className="fw-semibold"),
                html.Div(
                    [
                        html.Span("Absolute CBE (eq): "),
                        html.Span(id="cb-abs", className="fw-bold text-primary"),
                    ],
                    className="mb-3",
                ),
                html.Div(
                    [
                        html.Span("Relative CBE (%): "),
                        dbc.Badge(id="cb-rel", pill=True, className="fs-5"),
                    ],
                ),
            ]
        ),
        class_name="shadow-sm h-100",
        style={"borderRadius": "1rem"},
    )

    references = html.Div(
        [
            dcc.Markdown(REFS_CBE_MD, mathjax=True, style={"fontSize": "0.9rem"}),
        ],
        style={"maxWidth": "760px", "margin": "4rem auto 0"},
        className="text-start",
    )

    body = html.Div(
        dbc.Container(
            [
                intro,  # ← inserted just before the two-column layout
                dbc.Row(
                    [
                        dbc.Col(inputs_card, lg=6),
                        dbc.Col(
                            results_card,
                            lg=4,
                            class_name="mt-4 mt-lg-0",
                        ),
                    ],
                    class_name="justify-content-center",
                ),
                references   # added to the app
            ],
            style={
                "maxWidth": "1160px",
                "paddingTop": "3rem",   # a touch more breathing space
                "paddingBottom": "4rem",
            },
        ),
        style={"flex": "1 0 auto"},
    )

    return html.Div(
        [header, body, Footer()],
        style={
            "display": "flex",
            "flexDirection": "column",
            "minHeight": "100vh",
        },
    )
# ───────── callbacks ─────────
@app.callback(Output("cb-density-div", "style"), Input("cb-unit", "value"))
def _toggle_density(unit):
    return {} if unit == "mmol/L" else {"display": "none"}

for _ion in ["cb-mg", "cb-ca", "cb-na", "cb-k", "cb-ta", "cb-cl", "cb-so4", "cb-no3"]:
    inc_id, dec_id = f"inc-{_ion}", f"dec-{_ion}"

    @app.callback(Output(_ion, "value"), Input(inc_id, "n_clicks"), Input(dec_id, "n_clicks"), State(_ion, "value"), prevent_initial_call=True)
    def _stepper(inc, dec, value, _ion=_ion, inc_id=inc_id, dec_id=dec_id):
        try:
            value_str = str(value).strip().replace(",", ".") if value is not None else "0"
            value = float(value_str)
        except ValueError:
            value = 0.0
        trigger = ctx.triggered_id
        if trigger == inc_id:
            value += 0.5
        elif trigger == dec_id:
            value = max(0, value - 0.5)
        return round(value, 2)

@app.callback(
    Output("cb-abs", "children"),
    Output("cb-rel", "children"),
    Output("cb-rel", "color"),
    [
        Input("cb-mg", "value"), Input("cb-ca", "value"),
        Input("cb-na", "value"), Input("cb-k", "value"),
        Input("cb-ta", "value"), Input("cb-cl", "value"),
        Input("cb-so4", "value"), Input("cb-no3", "value"),
        Input("cb-unit", "value"), Input("cb-density", "value"),
    ],
)
def _update_balance(mg, ca, na, k, ta, cl, so4, no3, unit, density):
    """Compute absolute and relative charge-balance error (CBE)."""

    # ── sanity checks ───────────────────────────────────────────────
    if None in (mg, ca, na, k, ta, cl, so4, no3) or (
        unit == "mmol/L" and density is None
    ):
        raise PreventUpdate

    # convert everything to mmol · kg⁻¹  (if user chose mmol · L⁻¹)
    factor = 1.0 / float(density) if unit == "mmol/L" else 1.0
    mg, ca, na, k, ta, cl, so4, no3 = [
        float(x) * factor for x in (mg, ca, na, k, ta, cl, so4, no3)
    ]

    # ── equivalents of charge (mol · kg⁻¹) ──────────────────────────
    cations_eq = (mg * 2 + ca * 2 + na + k) / 1000.0
    anions_eq  = (cl + so4 * 2 + no3) / 1000.0 + ta/1000  # TA also needs to be divided by 1000

    # ── charge-balance error ────────────────────────────────────────
    cbe_total = cations_eq - anions_eq                 # error in charge eq
    denom   = (cations_eq + anions_eq)                 # sum of it
    cbe_rel = (cbe_total / denom)*100 if denom else 0.0   # relative error in %

    # badge colour: red if outside ±5 %
    colour = "danger" if cbe_rel > 5 else "success"

    return f"{cbe_total:.4f}", f"{cbe_rel:.2f} %", colour


# ────────────────────────  PAGE ROUTING CALLBACK ─────────────────────────
@app.callback(Output("page-layout", "children"), Input("url", "pathname"))
def display_page(pathname: str):
    if pathname in ("/", ""):
        return home_layout()
    if pathname == "/carbonate-system-modeling":
        return calc_layout()
    if pathname == "/xrf":
        return xrf_layout()
    if pathname == "/mineral-dissolution":
        return mineral_layout()
    if pathname == "/forsterite-dissolution":
        return forsterite_dissolution_layout()
    if pathname == "/bjerrum-plot-explorer":
        return bjerrum_layout()
    if pathname == "/charge-balance":
        return cb_layout()
    if pathname == "/carbonate-system-modeling-seawater":
        return seawater_layout()
    if pathname == "/dic-pCO2":
        return dic_pco2_layout()
    if pathname == "/impressum":
        return legal_layout(IMPRESSUM_MD, "Impressum", pathname)
    if pathname == "/datenschutz":
        return legal_layout(DATENSCHUTZ_MD, "Datenschutz", pathname)
    if pathname == "/barrierefreiheit":
        return legal_layout(BARRECHT_MD, "Barrierefreiheit", pathname)

    # 404 fallback
    return html.Div(
        [
            SiteHeader("404 – Seite nicht gefunden", [("Home", "/")]),
            dbc.Container(html.H3("Die angeforderte Seite existiert nicht."), style={"maxWidth": MAX_WIDTH}),
            Footer(),
        ],
        style={"display": "flex", "flexDirection": "column", "flex": "1 0 auto"},
    )

# ─────────────────────────────  DEV ENTRY‑POINT  ────────────────────────────
if __name__ == "__main__":
    app.run(debug=False)
