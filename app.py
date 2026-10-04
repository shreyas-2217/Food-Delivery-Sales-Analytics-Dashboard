"""
Food Delivery Sales Analytics Dashboard — Streamlit app (Swiggy food orders)
---------------------------------------------------------------------
Filterable view of order revenue by period, restaurant, dish, city and
category. Queries are parameterised against SQLite (data/retail.db).

Run locally:
    streamlit run app.py
"""

from __future__ import annotations

import html as _html
import math
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.query_helpers import (
    build_where_clause,
    ensure_db,
    get_filter_bounds,
    load_sql,
    run_query,
)

st.set_page_config(
    page_title="Food Delivery Sales Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto",
)

# ----------------------------------------------------------------------------
# Design tokens
# ----------------------------------------------------------------------------
INK = "#0E1116"
INK2 = "#344054"
MUTED = "#667085"
FAINT = "#98A2B3"
RULE = "#E4E7EC"
RULE2 = "#EEF1F4"
CANVAS = "#F4F5F7"
SURFACE = "#FFFFFF"
TEAL = "#0B5F55"
TEAL_SOFT = "#9FC3BC"
AMBER = "#B54708"
POS = "#0E7C66"
NEG = "#B42318"

SANS = '"IBM Plex Sans", system-ui, sans-serif'
MONO = '"IBM Plex Mono", ui-monospace, Menlo, monospace'
DISP = '"Archivo", "IBM Plex Sans", system-ui, sans-serif'

# rating scale: lighter teal = lower rating, deep teal = higher
SEQ_RATING = ["#D6E4DF", "#79B9AC", "#127C6B", "#0B5F55"]
# order-volume scale for dish chart
SEQ_VOLUME = ["#D6E4DF", "#79B9AC", "#127C6B", "#0B5F55"]

CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

:root{
  --ink:#0E1116; --ink2:#344054; --muted:#667085; --faint:#98A2B3;
  --rule:#E4E7EC; --rule2:#EEF1F4; --canvas:#F4F5F7; --surface:#FFFFFF;
  --teal:#0B5F55; --teal-l:#5FC3B4; --amber:#B54708;
  --pos:#0E7C66; --neg:#B42318;
  --mono:"IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace;
  --sans:"IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --disp:"Archivo", "IBM Plex Sans", system-ui, sans-serif;
}

/* ---- canvas + type scale ------------------------------------------------ */
.stApp{ background:var(--canvas); color:var(--ink2); }
.stApp, .stApp p, .stApp li, .stApp label, .stApp textarea, .stApp input{
  font-family:var(--sans);
}
.stApp h1, .stApp h2, .stApp h3, .stApp h4{
  font-family:var(--disp); color:var(--ink); font-weight:600; letter-spacing:-0.015em;
}
.stApp p, .stApp li{ color:var(--ink2); }
[data-testid="stMarkdown"], [data-testid="stMarkdownContainer"]{ max-width:none; }
.stApp p, .stApp li{ max-width:104ch; }
.stApp :focus-visible{ outline:2px solid var(--teal); outline-offset:2px; }

/* ---- filter rail -------------------------------------------------------- */
section[data-testid="stSidebar"]{
  background:var(--surface); border-right:1px solid var(--rule);
}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{ color:var(--ink2); }
[data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] > label{
  font-family:var(--sans); font-weight:600; font-size:13px; color:var(--ink);
}
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p{ font-size:12.5px; }
.rail-brand{
  font-family:var(--disp); font-size:15px; font-weight:600; color:var(--ink);
  letter-spacing:-0.01em; padding-bottom:10px; margin-bottom:14px;
  border-bottom:2px solid var(--teal); line-height:1.25;
}
.rail-brand span{
  display:block; font-family:var(--mono); font-size:10.5px; font-weight:400;
  letter-spacing:.08em; color:var(--faint); margin-top:5px;
}
.rail-eyebrow{
  font-family:var(--mono); font-size:10.5px; letter-spacing:.16em;
  text-transform:uppercase; color:var(--muted); margin:2px 0 10px;
}
.rail-meta{ font-family:var(--mono); font-size:11.5px; color:var(--ink); display:grid; gap:5px; }
.rail-meta div{ display:flex; gap:10px; }
.rail-meta span{
  display:inline-block; width:76px; color:var(--faint);
  letter-spacing:.1em; font-size:10.5px; padding-top:2px;
}
.rail-note{
  font-family:var(--mono); font-size:10.5px; color:var(--faint);
  line-height:1.6; margin-top:10px;
}

/* ---- inputs ------------------------------------------------------------- */
[data-baseweb="base-input"], [data-baseweb="input"]{
  background:var(--surface); border-color:#D0D5DD !important;
}
[data-baseweb="tag"]{
  background:#EAF2F0; color:var(--teal); border:1px solid #CBE0DB;
  border-radius:6px; font-family:var(--mono); font-size:11.5px;
}
[data-baseweb="tag"] button{ color:var(--teal); }
[data-testid="stDateInput"]{ font-family:var(--mono); font-size:13px; }

/* ---- buttons ------------------------------------------------------------ */
.stButton > button{
  border-radius:8px; font-family:var(--sans); font-weight:600; font-size:13px;
  border:1px solid var(--rule); background:var(--surface); color:var(--ink);
}
.stButton > button:hover{
  border-color:#B9C0CA; background:#FAFBFC; color:var(--ink);
}
.stButton > button[kind="primary"]{
  background:var(--teal); border-color:var(--teal); color:#FFFFFF;
}
.stButton > button[kind="primary"]:hover{
  background:#094A42; border-color:#094A42; color:#FFFFFF;
}

/* ---- tabs --------------------------------------------------------------- */
[data-testid="stTabs"] [role="tablist"]{ gap:2px; column-gap:6px; }
[data-testid="stTabs"] [role="tab"]{
  font-family:var(--sans); font-weight:600; font-size:13.5px; color:var(--muted);
  background:transparent; padding:12px 6px; margin-right:10px;
}
[data-testid="stTabs"] [role="tab"]:hover, [data-testid="stTabs"] [role="tab"][aria-selected="true"]{
  color:var(--ink); background:transparent;
}
[data-testid="stTabs"]{ border-bottom:1px solid var(--rule); }

/* ---- masthead ----------------------------------------------------------- */
.masthead{
  background:#0E1116; border-radius:12px; padding:26px 30px 24px;
  display:flex; gap:30px; justify-content:space-between; align-items:flex-end;
  flex-wrap:wrap; margin:4px 0 14px;
}
.masthead .mh-main{ min-width:0; }
.masthead .mh-eyebrow{
  font-family:var(--mono); font-size:10.5px; letter-spacing:.2em;
  text-transform:uppercase; color:var(--teal-l); margin-bottom:12px;
}
.masthead h1{
  font-family:var(--disp) !important; font-size:31px !important; font-weight:600;
  color:#FFFFFF !important; margin:0 0 10px; letter-spacing:-0.025em; line-height:1.08;
}
.masthead .mh-scope{
  font-family:var(--mono); font-size:11.5px; color:#98A2B3 !important;
  letter-spacing:.04em; margin:0 0 12px;
}
.masthead p.mh-brief{
  font-size:15px; line-height:1.55; color:#D0D5DD !important; margin:0;
  max-width:64ch;
}
.masthead p.mh-brief b{ color:#FFFFFF; font-weight:600; }
.masthead .mh-spec{
  display:grid; gap:7px; font-family:var(--mono); font-size:11px; text-align:right;
}
.masthead .mh-spec div{ display:flex; gap:14px; justify-content:flex-end; }
.masthead .mh-spec span{ color:#667085; letter-spacing:.12em; font-size:10px; padding-top:1px; }
.masthead .mh-spec b{ color:#E4E7EC; font-weight:500; }

@media (max-width: 1180px){
  .masthead{ padding:22px; }
  .masthead p.mh-brief{ max-width:none; }
  .masthead .mh-spec{ text-align:left; }
  .masthead .mh-spec div{ justify-content:flex-start; }
}

/* ---- KPI ledger --------------------------------------------------------- */
.ledger{
  background:var(--surface); border:1px solid var(--rule); border-radius:10px;
  display:grid; grid-template-columns:repeat(4,1fr); overflow:hidden;
  box-shadow:0 1px 2px rgba(16,24,40,.05); margin-bottom:16px;
}
.ledger .cell{ padding:16px 18px 15px; border-left:1px solid var(--rule); }
.ledger .cell:first-child{ border-left:0; }
.cell-top{ display:flex; justify-content:space-between; align-items:flex-start; gap:10px; }
.cell-label{
  font-family:var(--mono); font-size:10.5px; letter-spacing:.14em;
  text-transform:uppercase; color:var(--muted);
}
.cell-value{
  font-family:var(--mono); font-size:25px; font-weight:600; color:var(--ink);
  letter-spacing:-0.02em; margin:10px 0 7px; font-variant-numeric:tabular-nums;
}
.cell-delta, .cell-sub{ font-family:var(--mono); font-size:11.5px; line-height:1.5; }
.cell-delta.pos{ color:var(--pos); }
.cell-delta.neg{ color:var(--neg); }
.cell-delta.flat{ color:var(--muted); }
.cell-delta span, .cell-sub span{ color:var(--faint); }
.cell-sub{ color:var(--muted); }
.spark{ display:block; }

@media (max-width: 960px){
  .ledger{ grid-template-columns:repeat(2,1fr); }
  .ledger .cell:nth-child(3){ border-left:0; }
  .ledger .cell:nth-child(n+3){ border-top:1px solid var(--rule); }
}
@media (max-width: 560px){
  .ledger{ grid-template-columns:1fr; }
  .ledger .cell{ border-left:0; border-top:1px solid var(--rule); }
  .ledger .cell:first-child{ border-top:0; }
  .masthead h1{ font-size:25px; }
}

/* ---- panels ------------------------------------------------------------- */
[data-testid="stBorderWrapper"],
[data-testid="stVerticalBlockBorderWrapper"]{
  background:var(--surface); border:1px solid var(--rule) !important;
  border-radius:10px; box-shadow:0 1px 2px rgba(16,24,40,.05);
}
.p-eyebrow{
  font-family:var(--mono); font-size:10.5px; letter-spacing:.16em;
  text-transform:uppercase; color:var(--muted); margin:0 0 7px;
}
.p-title{
  font-family:var(--disp); font-size:17px; font-weight:600; color:var(--ink);
  line-height:1.3; margin:0;
}
.p-sub{ font-family:var(--mono); font-size:11.5px; color:var(--faint); margin:5px 0 0; }
.insight{
  border-top:1px solid var(--rule2); margin-top:14px; padding-top:12px;
  font-size:13.5px; line-height:1.6; color:var(--ink2);
}
.ins-tag{
  font-family:var(--mono); font-size:9.5px; letter-spacing:.16em; color:var(--teal);
  background:#EAF2F0; border:1px solid #CBE0DB; border-radius:4px;
  padding:2px 7px; margin-right:9px; vertical-align:1.5px;
}
.insight b{ color:var(--ink); font-weight:600; }

/* ---- rank list ---------------------------------------------------------- */
.rank-list{ display:grid; min-width:0; overflow:hidden; }
.rank-row{
  display:grid; grid-template-columns:24px minmax(0,1.2fr) minmax(0,1.6fr) max-content max-content;
  align-items:center; gap:10px; padding:9px 0; border-bottom:1px solid var(--rule2);
}
.rank-row:last-child{ border-bottom:0; }
.rank-row > *{ min-width:0; }
.rk{ font-family:var(--mono); font-size:11px; color:var(--teal); }
.nm{
  color:var(--ink); font-weight:500; font-size:13.5px;
  overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
}
.bar{ height:6px; background:var(--rule2); border-radius:3px; overflow:hidden; }
.bar i{ display:block; height:100%; background:var(--teal); border-radius:3px; }
.vl{
  font-family:var(--mono); font-size:12.5px; color:var(--ink); text-align:right;
  font-variant-numeric:tabular-nums; white-space:nowrap;
}
.sh{
  font-family:var(--mono); font-size:11px; color:var(--muted); text-align:right;
  white-space:nowrap;
}
@media (max-width: 640px){
  .rank-row{ grid-template-columns:24px 1fr 84px; }
  .rank-row .bar, .rank-row .sh{ display:none; }
}

/* ---- stats + empty state ------------------------------------------------ */
.stat{
  background:#FBFBFC; border:1px solid var(--rule); border-radius:8px;
  padding:13px 15px; height:100%;
}
.stat span{
  display:block; font-family:var(--mono); font-size:10px; letter-spacing:.14em;
  text-transform:uppercase; color:var(--muted); margin-bottom:7px;
}
.stat b{
  font-family:var(--mono); font-size:21px; font-weight:600; color:var(--ink);
  font-variant-numeric:tabular-nums;
}
.stat em{
  display:block; font-style:normal; font-family:var(--mono); font-size:11px;
  color:var(--faint); margin-top:5px;
}
.empty{
  border:1px dashed var(--rule); border-radius:8px; padding:28px 24px;
  text-align:center; background:#FBFBFC;
}
.empty b{
  display:block; font-family:var(--disp); font-size:15px; color:var(--ink);
  margin-bottom:6px;
}
.empty span{ font-size:13px; color:var(--muted); }

/* ---- expander + code ---------------------------------------------------- */
[data-testid="stExpander"]{
  border:1px solid var(--rule); border-radius:8px; background:#FBFBFC;
}
[data-testid="stExpander"] details > summary,
[data-testid="stExpander"] details > summary span:not([data-testid="stIconMaterial"]){
  font-family:var(--mono); font-size:11.5px; letter-spacing:.06em; color:var(--muted);
}
[data-testid="stExpander"] details > summary p{
  font-family:var(--mono); font-size:11.5px !important; letter-spacing:.06em;
  color:var(--muted); margin:0; line-height:1.4;
}
[data-testid="stExpander"] details > summary:hover,
[data-testid="stExpander"] details > summary:hover p,
[data-testid="stExpander"] details > summary:hover span:not([data-testid="stIconMaterial"]){
  color:var(--ink);
}
[data-testid="stExpander"] details > summary [data-testid="stIconMaterial"]{
  font-size:16px !important; color:var(--muted);
}
[data-testid="stCodeBlock"]{
  background:#0E1116 !important; border:1px solid #1E242B; border-radius:8px;
}
[data-testid="stCodeBlock"] pre, [data-testid="stCodeBlock"] code{
  font-family:var(--mono) !important; font-size:12px; color:#C9D1D9;
}
[data-testid="stCodeBlock"] header button{ color:#8B949E !important; }

/* ---- misc --------------------------------------------------------------- */
.divider{ border-top:1px solid var(--rule); }
.footnote{
  border-top:1px solid var(--rule); padding-top:16px;
  font-size:12.5px; line-height:1.65; color:var(--muted);
}
.footnote b{ color:var(--ink2); font-weight:600; }
.foot-credit{
  font-family:var(--mono); font-size:11px; letter-spacing:.06em;
  color:var(--faint); margin-top:10px;
}
"""

st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = PROJECT_ROOT / "data" / "retail.db"

# ----------------------------------------------------------------------------
# Data access
# ----------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def cached_bounds() -> dict:
    """Min/max date and city list for the filter rail."""
    return get_filter_bounds(DB_PATH)


@st.cache_data(show_spinner=False)
def cached_profile() -> dict:
    """Whole-dataset facts used for the coverage block and spec list."""
    sql = """
    SELECT COUNT(*) AS lines, COUNT(DISTINCT City) AS cities,
           COUNT(DISTINCT Restaurant) AS outlets, COUNT(DISTINCT Item) AS items,
           MIN(date(OrderDate)) AS min_d, MAX(date(OrderDate)) AS max_d,
           ROUND(SUM(Revenue), 2) AS revenue
    FROM orders
    """
    return run_query(sql, db_path=DB_PATH).iloc[0].to_dict()


@st.cache_data(show_spinner=True)
def cached_query(sql: str, params: tuple) -> pd.DataFrame:
    """Run a SELECT with parameters, cached per filter combination."""
    return run_query(sql, params, db_path=DB_PATH)


# ----------------------------------------------------------------------------
# Formatting helpers
# ----------------------------------------------------------------------------


def esc(value) -> str:
    """Escape dynamic text before it goes into HTML."""
    return _html.escape(str(value))


def inr(x, decimals: int = 0) -> str:
    """Full rupee amount with grouping: 52,984,174."""
    try:
        return f"₹{float(x):,.{decimals}f}"
    except (TypeError, ValueError):
        return "--"


def num(x, decimals: int = 0) -> str:
    """Grouped digits without currency for table cells: 5,16,114.

    Streamlit 1.49 NumberColumn only accepts printf patterns (%.0f),
    which cannot print thousands separators, so money columns are
    pre-formatted with this helper and shown as text.
    """
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "--"
    if pd.isna(v):
        return "--"
    return f"{v:,.{decimals}f}"


def inr_compact(x) -> str:
    """Short rupee amount for axes, tooltips and headlines: 68.2L / 5.30 Cr."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "--"
    a = abs(v)
    if a >= 1e7:
        return f"₹{v / 1e7:,.2f} Cr".replace(".00 Cr", " Cr")
    if a >= 1e5:
        return f"₹{v / 1e5:,.1f} L".replace(".0 L", " L")
    if a >= 1e3:
        return f"₹{v / 1e3:,.0f} K"
    return f"₹{v:,.0f}"


def nice_ticks(lo: float, hi: float, n: int = 5) -> list[float]:
    """Round axis ticks covering [lo, hi]."""
    if hi <= lo:
        hi = lo + 1
    raw = (hi - lo) / max(n, 1)
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    step = mag
    for mult in (1, 2, 2.5, 5, 10):
        if raw <= mult * mag:
            step = mult * mag
            break
    start = math.floor(lo / step) * step
    ticks, t = [], start
    guard = 0
    while t <= hi + step * 0.5 and guard < 50:
        if t >= lo - step * 0.5:
            ticks.append(round(t, 10))
        t += step
        guard += 1
    return ticks or [lo, hi]


def _trace_values(fig, axis: str) -> list[float]:
    out: list[float] = []
    for trace in fig.data:
        arr = getattr(trace, axis, None)
        if arr is None:
            continue
        if isinstance(arr, (str, bytes)):
            arr = [arr]
        try:
            iterator = iter(arr)
        except TypeError:
            iterator = iter([arr])
        for v in iterator:
            try:
                fv = float(v)
            except (TypeError, ValueError):
                continue
            if not math.isnan(fv):
                out.append(fv)
    return out


def configure(
    fig,
    *,
    height: int = 340,
    value_axis: str | None = None,
    money: bool = False,
    pct: bool = False,
    zero_base: bool = False,
    legend: bool = False,
    hover: str | None = None,
    x_tickangle: int | None = None,
    y_range: tuple[float, float] | None = None,
    n_ticks: int = 5,
):
    """Apply one chart language across every figure in the app."""
    fig.update_layout(
        font=dict(family=SANS, size=12.5, color=INK2),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=4, r=4, t=14, b=4),
        height=height,
        showlegend=legend,
        hoverlabel=dict(
            bgcolor=INK, bordercolor=INK,
            font=dict(family=MONO, size=11.5, color="#FFFFFF"),
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0,
            font=dict(size=11.5, family=SANS, color=MUTED),
        ),
    )
    fig.update_xaxes(
        showgrid=False, zeroline=False, showline=True, linecolor=RULE,
        ticks="outside", tickcolor=RULE, ticklen=4,
        tickfont=dict(family=MONO, size=10.5, color=MUTED),
    )
    fig.update_yaxes(
        showgrid=True, gridcolor=RULE2, gridwidth=1, zeroline=False, showline=False,
        tickfont=dict(family=MONO, size=10.5, color=MUTED),
    )
    if x_tickangle is not None:
        fig.update_xaxes(tickangle=x_tickangle)
    # units live in the panel sub-line, never on the axes
    fig.update_xaxes(title_text=None)
    fig.update_yaxes(title_text=None)

    if value_axis in ("x", "y"):
        vals = _trace_values(fig, value_axis)
        if value_axis == "x":
            fig.update_xaxes(showgrid=True, gridcolor=RULE2, showline=False)
            fig.update_yaxes(showgrid=False, showline=True, linecolor=RULE,
                             ticks="outside", tickcolor=RULE, ticklen=4)
        if vals:
            lo, hi = min(vals), max(vals)
            if y_range is not None:
                lo, hi = y_range
            elif zero_base:
                lo, hi = min(lo, 0.0), max(hi, 0.0)
                pad = (hi - lo) or 1
                hi = hi + pad * 0.12
                if lo < 0:
                    lo = lo - pad * 0.12
            else:
                span = (hi - lo) or (abs(hi) or 1)
                lo, hi = lo - span * 0.15, hi + span * 0.12
            ticks = nice_ticks(lo, hi, n_ticks)
            if money:
                text = [inr_compact(t) for t in ticks]
            elif pct:
                text = [f"{t:g}%" for t in ticks]
            else:
                text = None
            updater = fig.update_xaxes if value_axis == "x" else fig.update_yaxes
            if text:
                updater(tickvals=ticks, ticktext=text, range=[lo, hi])
            else:
                updater(tickvals=ticks, range=[lo, hi])

    if hover:
        fig.update_traces(hovertemplate=hover)
    return fig


def month_label(m) -> str:
    """2025-01 -> Jan 2025."""
    return pd.to_datetime(m).strftime("%b %Y")


def bucket_label(b) -> str:
    """Format a chart bucket for axis ticks and prose."""
    ts = pd.to_datetime(b)
    return ts.strftime("%d %b") if bucket_fmt.endswith("%d") else ts.strftime("%b %Y")


def bucket_ticks(fig, values, labels, max_ticks: int = 12):
    """One tick per bucket, evenly thinned, none dropped at the edges."""
    values = [str(v) for v in values]
    n = len(values)
    if n == 0:
        return
    step = max(1, math.ceil(n / max_ticks))
    idx = [i for i in range(0, n, step)]
    if (n - 1) not in idx:
        idx.append(n - 1)
    fig.update_xaxes(
        tickmode="array",
        tickvals=[values[i] for i in idx],
        ticktext=[labels[i] for i in idx],
        tickangle=0,
    )
    first, last = pd.to_datetime(values[0]), pd.to_datetime(values[-1])
    span = (last - first) or pd.Timedelta(days=1)
    fig.update_xaxes(range=[(first - span * 0.05).strftime("%Y-%m-%d"),
                            (last + span * 0.07).strftime("%Y-%m-%d")])


def sparkline(values, color: str = TEAL, w: int = 94, h: int = 26) -> str:
    """Tiny inline SVG trend line for a KPI cell."""
    vals = []
    for v in values:
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        if not math.isnan(fv):
            vals.append(fv)
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1.0
    pts = []
    for i, v in enumerate(vals):
        x = i * (w / (len(vals) - 1))
        y = (h - 3) - ((v - lo) / rng) * (h - 6)
        pts.append(f"{x:.1f},{y:.1f}")
    path = "M" + " L".join(pts)
    lx, ly = pts[-1].split(",")
    return (
        f'<svg class="spark" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'aria-hidden="true" focusable="false">'
        f'<path d="{path}" fill="none" stroke="{color}" stroke-width="1.5" '
        f'stroke-linejoin="round" stroke-linecap="round"/>'
        f'<circle cx="{lx}" cy="{ly}" r="2.4" fill="{color}"/></svg>'
    )


# ----------------------------------------------------------------------------
# Layout helpers
# ----------------------------------------------------------------------------


def panel(eyebrow: str, title: str, sub: str = ""):
    """A white card with an eyebrow (scope), a heading and an optional sub-line."""
    box = st.container(border=True)
    with box:
        sub_html = f'<div class="p-sub">{esc(sub)}</div>' if sub else ""
        st.markdown(
            f'<div class="p-eyebrow">{esc(eyebrow)}</div>'
            f'<div class="p-title">{esc(title)}</div>{sub_html}',
            unsafe_allow_html=True,
        )
    return box


def insight(text: str):
    """Hairline-ruled reading line at the bottom of a panel."""
    st.markdown(
        f'<div class="insight"><span class="ins-tag">INSIGHT</span>{text}</div>',
        unsafe_allow_html=True,
    )


def empty_state(title: str, hint: str = ""):
    hint_html = f"<span>{esc(hint)}</span>" if hint else ""
    st.markdown(
        f'<div class="empty"><b>{esc(title)}</b>{hint_html}</div>',
        unsafe_allow_html=True,
    )


def sql_box(files: list[str] | None = None, inline: str = ""):
    """Collapse the SQL behind a panel into one expander."""
    label = "View query"
    if files:
        label += " · " + ", ".join(files)
    with st.expander(label):
        if inline:
            st.code(inline.strip(), language="sql")
        for name in files or []:
            try:
                st.code(load_sql(name).strip(), language="sql")
            except Exception:
                st.caption(f"sql/{name} could not be read.")


def stat_row(items: list[tuple[str, str, str]], columns: int | None = None):
    """Row of small labelled figures (label, value, foot)."""
    cols = st.columns(columns or len(items))
    for col, (label, value, foot) in zip(cols, items):
        col.markdown(
            f'<div class="stat"><span>{esc(label)}</span><b>{esc(value)}</b>'
            f'<em>{esc(foot)}</em></div>',
            unsafe_allow_html=True,
        )


def rank_list(
    df: pd.DataFrame,
    name_col: str,
    value_col: str,
    share_col: str | None = None,
    formatter=inr_compact,
) -> str:
    """Leaderboard rows: rank, name, share bar, value, share of total."""
    if df.empty:
        return ""
    top = float(df[value_col].max() or 1)
    rows = []
    for i, (_, row) in enumerate(df.iterrows(), start=1):
        width = 100 * float(row[value_col]) / top
        share = f"{float(row[share_col]):.1f}%" if share_col else ""
        rows.append(
            '<div class="rank-row">'
            f'<span class="rk">{i:02d}</span>'
            f'<span class="nm">{esc(row[name_col])}</span>'
            f'<span class="bar"><i style="width:{width:.1f}%"></i></span>'
            f'<span class="vl">{esc(formatter(row[value_col]))}</span>'
            f'<span class="sh">{share}</span>'
            "</div>"
        )
    return f'<div class="rank-list">{"".join(rows)}</div>'


# ----------------------------------------------------------------------------
# Bootstrap
# ----------------------------------------------------------------------------

try:
    ensure_db()
except FileNotFoundError as e:
    st.error("Database not found.")
    st.code(str(e))
    st.info("Place the Swiggy file in data/, then run python -m src.data_prep.")
    st.stop()
except Exception as e:
    st.error(f"Could not open database: {e}")
    st.stop()

try:
    bounds = cached_bounds()
    profile = cached_profile()
except Exception as e:
    st.error(f"Could not read the orders table: {e}")
    st.info("Run python -m src.data_prep first to create the orders table.")
    st.stop()

MIN_DATE = pd.to_datetime(bounds["min_date"]).date()
MAX_DATE = pd.to_datetime(bounds["max_date"]).date()
ALL_CITIES: list[str] = bounds.get("cities") or bounds.get("countries", [])

# Guard against empty or unreadable order dates (NaT would crash the widgets
# below with an obscure formatting error). Fail here with the actual state.
if (
    not isinstance(MIN_DATE, date)
    or not isinstance(MAX_DATE, date)
    or pd.isna(MIN_DATE)
    or pd.isna(MAX_DATE)
    or MIN_DATE > MAX_DATE
):
    st.error(
        "Order dates are missing or unreadable. "
        f"Got range {bounds.get('min_date')!r} to {bounds.get('max_date')!r}."
    )
    st.info("Rebuild the data: place the Swiggy file in data/, run python -m src.data_prep, and relaunch.")
    st.stop()

# ----------------------------------------------------------------------------
# Filter rail
# ----------------------------------------------------------------------------


def apply_quick_range():
    choice = st.session_state.get("quick_range")
    if not choice:
        return
    days = {"90d": 90, "30d": 30}.get(choice)
    end = MAX_DATE
    start = MIN_DATE if days is None else max(MIN_DATE, end - timedelta(days=days - 1))
    st.session_state["start_d"] = start
    st.session_state["end_d"] = end


def reset_filters():
    st.session_state["start_d"] = MIN_DATE
    st.session_state["end_d"] = MAX_DATE
    st.session_state["cities_sel"] = []
    st.session_state["quick_range"] = None


if "start_d" not in st.session_state:
    st.session_state["start_d"] = MIN_DATE
if "end_d" not in st.session_state:
    st.session_state["end_d"] = MAX_DATE
if "cities_sel" not in st.session_state:
    st.session_state["cities_sel"] = []

with st.sidebar:
    st.markdown(
        '<div class="rail-brand">Food Delivery Sales Analytics'
        "<span>Swiggy order data · Jan–Aug 2025</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="rail-eyebrow">Filters</div>', unsafe_allow_html=True)

    st.segmented_control(
        "Quick range",
        options=["All", "90d", "30d"],
        key="quick_range",
        on_change=apply_quick_range,
    )

    # NOTE: pass an explicit in-bounds default date. Newer Streamlit
    # versions validate the widget default against min/max at build time,
    # and the implicit default (today) lies outside this 2025 dataset.
    start_d: date = st.date_input(
        "Start date",
        value=max(MIN_DATE, min(st.session_state["start_d"], MAX_DATE)),
        key="start_d",
        min_value=MIN_DATE, max_value=MAX_DATE,
    )
    end_d: date = st.date_input(
        "End date",
        value=max(MIN_DATE, min(st.session_state["end_d"], MAX_DATE)),
        key="end_d",
        min_value=MIN_DATE, max_value=MAX_DATE,
    )

    selected_cities: list[str] = st.multiselect(
        "Cities",
        options=ALL_CITIES,
        key="cities_sel",
        help="Leave empty to include every city in the dataset.",
    )

    st.button("Reset filters", on_click=reset_filters, width="stretch")

    st.divider()
    st.markdown('<div class="rail-eyebrow">Coverage</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="rail-meta">'
        f'<div><span>PERIOD</span><b>Jan – Aug 2025</b></div>'
        f'<div><span>CITIES</span><b>{int(profile["cities"]):,}</b></div>'
        f'<div><span>OUTLETS</span><b>{int(profile["outlets"]):,}</b></div>'
        f'<div><span>LINES</span><b>{int(profile["lines"]):,}</b></div>'
        f'<div><span>REVENUE</span><b>{inr_compact(profile["revenue"])}</b></div>'
        "</div>"
        '<div class="rail-note">One row is one order line.<br>'
        "Revenue is the item price on that line.</div>",
        unsafe_allow_html=True,
    )

if start_d > end_d:
    st.sidebar.error("Start date must be on or before end date.")
    st.stop()

# ----------------------------------------------------------------------------
# Query scope: current window and the equally long window before it
# ----------------------------------------------------------------------------

START_S = start_d.strftime("%Y-%m-%d")
END_S = end_d.strftime("%Y-%m-%d")
WHERE, PARAMS = build_where_clause(START_S, END_S, selected_cities)

span_days = (end_d - start_d).days + 1
prev_end = start_d - timedelta(days=1)
prev_start = prev_end - timedelta(days=span_days - 1)
has_prev = prev_end >= MIN_DATE and prev_start >= MIN_DATE
if has_prev:
    PREV_WHERE, PREV_PARAMS = build_where_clause(
        prev_start.strftime("%Y-%m-%d"), prev_end.strftime("%Y-%m-%d"), selected_cities
    )
else:
    PREV_WHERE, PREV_PARAMS = "WHERE 1 = 0", ()

kpi_sql = f"""
SELECT SUM(Revenue) AS revenue, COUNT(*) AS records,
       COUNT(DISTINCT Restaurant) AS outlets
FROM orders {WHERE}
"""
kpi = cached_query(kpi_sql, tuple(PARAMS)).iloc[0]
total_rev = float(kpi["revenue"] or 0)
total_records = int(kpi["records"] or 0)
total_outlets = int(kpi["outlets"] or 0)
aov = (total_rev / total_records) if total_records else 0

if has_prev:
    prev_kpi = cached_query(
        f"SELECT SUM(Revenue) AS revenue, COUNT(*) AS records, "
        f"COUNT(DISTINCT Restaurant) AS outlets FROM orders {PREV_WHERE}",
        tuple(PREV_PARAMS),
    ).iloc[0]
    prev_rev = float(prev_kpi["revenue"] or 0)
    prev_records = int(prev_kpi["records"] or 0)
    prev_outlets = int(prev_kpi["outlets"] or 0)
    prev_aov = (prev_rev / prev_records) if prev_records else 0
else:
    prev_rev = prev_records = prev_outlets = prev_aov = 0

bucket_fmt = "%Y-%m-%d" if span_days <= 62 else "%Y-%m"
bucket_sql = f"""
SELECT strftime('{bucket_fmt}', OrderDate) AS bucket,
       SUM(Revenue) AS revenue, COUNT(*) AS records,
       COUNT(DISTINCT Restaurant) AS outlets
FROM orders {WHERE}
GROUP BY bucket ORDER BY bucket
"""
df_buckets = cached_query(bucket_sql, tuple(PARAMS))
df_buckets["aov"] = df_buckets["revenue"] / df_buckets["records"].replace(0, float("nan"))

top_city = cached_query(
    f"SELECT City, ROUND(SUM(Revenue), 2) AS revenue FROM orders {WHERE} "
    f"GROUP BY City ORDER BY revenue DESC LIMIT 1",
    tuple(PARAMS),
)
if not top_city.empty:
    lead_city = str(top_city.iloc[0]["City"])
    lead_city_rev = float(top_city.iloc[0]["revenue"])
else:
    lead_city, lead_city_rev = "", 0.0

# ----------------------------------------------------------------------------
# Masthead
# ----------------------------------------------------------------------------

scope_bits = [
    f"{start_d.strftime('%d %b %Y')} – {end_d.strftime('%d %b %Y')}",
    f"{len(selected_cities)} of {len(ALL_CITIES)} cities" if selected_cities
    else f"All {len(ALL_CITIES)} cities",
    f"{total_records:,} order lines",
]
# The hosted demo builds from a small committed sample instead of the full
# file, so label it to keep the numbers honest. Full local builds stay quiet.
full_rows = int(cached_query("SELECT COUNT(*) AS n FROM orders", ()).iloc[0]["n"])
if full_rows < 100000:
    scope_bits.append("Demo uses a sample of the data")
scope_line = " · ".join(scope_bits)

if df_buckets.empty:
    brief = (
        "No orders fall inside this selection. Widen the date range or clear the "
        "city filter to bring data back."
    )
else:
    monthly = df_buckets["revenue"]
    lo_m, hi_m = float(monthly.min()), float(monthly.max())
    spread = (hi_m - lo_m) / monthly.mean() * 100 if monthly.mean() else 0
    parts = []
    if has_prev and prev_rev:
        move = (total_rev - prev_rev) / prev_rev * 100
        parts.append(
            f"Revenue is <b>{'up' if move >= 0 else 'down'} {abs(move):.1f}%</b> "
            f"against the {span_days} days before this window."
        )
    elif len(df_buckets) > 1:
        parts.append(
            f"Monthly revenue moves in a <b>{inr_compact(lo_m)}–{inr_compact(hi_m)}</b> band, "
            f"a {spread:.1f}% spread."
        )
    else:
        parts.append(f"Revenue in this window is <b>{inr_compact(total_rev)}</b>.")
    if lead_city:
        parts.append(
            f"<b>{esc(lead_city)}</b> leads with "
            f"{100 * lead_city_rev / total_rev:.1f}% of the total."
        )
    brief = " ".join(parts)

st.markdown(
    '<div class="masthead">'
    '<div class="mh-main">'
    '<div class="mh-eyebrow">Retail sales · Swiggy order data · Jan–Aug 2025</div>'
    "<h1>Food Delivery Sales Analytics Dashboard</h1>"
    f'<div class="mh-scope">{esc(scope_line)}</div>'
    f'<p class="mh-brief">{brief}</p>'
    "</div>"
    '<div class="mh-spec">'
    '<div><span>GRAIN</span><b>one row = one order line</b></div>'
    '<div><span>STORE</span><b>SQLite · parameterised SQL</b></div>'
    f'<div><span>LAST ORDER</span><b>{pd.to_datetime(profile["max_d"]).strftime("%d %b %Y")}</b></div>'
    "</div></div>",
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# KPI ledger
# ----------------------------------------------------------------------------


def delta_html(current: float, previous: float, fallback: str) -> str:
    """Change against the equally long prior window, else a period fact."""
    if not has_prev or not previous:
        return f'<div class="cell-sub">{fallback}</div>'
    change = (current - previous) / previous * 100
    if abs(change) < 0.05:
        return (
            f'<div class="cell-delta flat">— no change '
            f"<span>vs prior {span_days}d</span></div>"
        )
    cls = "pos" if change > 0 else "neg"
    arrow = "▲" if change > 0 else "▼"
    return (
        f'<div class="cell-delta {cls}">{arrow} {abs(change):.1f}% '
        f"<span>vs prior {span_days}d</span></div>"
    )


n_buckets = len(df_buckets)
if df_buckets.empty:
    fallback_revenue = fallback_lines = fallback_outlets = fallback_aov = "no data in range"
else:
    per_bucket = (
        f"{n_buckets} {'day' if bucket_fmt.endswith('%d') else 'month'}"
        f"{'' if n_buckets == 1 else 's'}"
    )
    fallback_revenue = f"{per_bucket} · {inr_compact(df_buckets['revenue'].mean())} average"
    fallback_lines = f"{span_days} days · {total_records / span_days:,.0f} lines a day"
    fallback_outlets = "distinct restaurant names in range"
    fallback_aov = "revenue ÷ order lines"


def cell(label: str, value: str, delta: str, series, series_color: str = TEAL) -> str:
    return (
        '<div class="cell">'
        f'<div class="cell-top"><span class="cell-label">{esc(label)}</span>'
        f"{sparkline(series, series_color)}</div>"
        f'<div class="cell-value">{esc(value)}</div>'
        f"{delta}"
        "</div>"
    )


ledger_html = '<div class="ledger">' + "".join([
    cell(
        "Revenue", inr(total_rev),
        delta_html(total_rev, prev_rev, fallback_revenue),
        df_buckets["revenue"] if not df_buckets.empty else [],
    ),
    cell(
        "Order lines", f"{total_records:,}",
        delta_html(total_records, prev_records, fallback_lines),
        df_buckets["records"] if not df_buckets.empty else [],
    ),
    cell(
        "Outlets", f"{total_outlets:,}",
        delta_html(total_outlets, prev_outlets, fallback_outlets),
        df_buckets["outlets"] if not df_buckets.empty else [],
    ),
    cell(
        "Avg line value", inr(aov, 2),
        delta_html(aov, prev_aov, fallback_aov),
        df_buckets["aov"] if not df_buckets.empty else [],
        AMBER,
    ),
]) + "</div>"
st.markdown(ledger_html, unsafe_allow_html=True)

if has_prev:
    st.markdown(
        f'<div class="p-sub">Deltas compare this window with '
        f"{prev_start.strftime('%d %b')} – {prev_end.strftime('%d %b %Y')} "
        "at the same length and city selection.</div>",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        '<div class="p-sub">This window starts at the first order in the dataset, '
        "so no earlier period exists for comparison.</div>",
        unsafe_allow_html=True,
    )

# ----------------------------------------------------------------------------
# Sections
# ----------------------------------------------------------------------------

tab_overview, tab_trend, tab_rest, tab_dish, tab_geo, tab_mix, tab_sql = st.tabs([
    "Overview", "Trends", "Restaurants", "Dishes",
    "Cities", "Categories & recency", "SQL explorer",
])

BUCKET_LABEL = "day" if bucket_fmt.endswith("%d") else "month"


def bucket_word(n: int) -> str:
    unit = BUCKET_LABEL
    return f"{n} {unit}" if n == 1 else f"{n} {unit}s"


# ---- Overview --------------------------------------------------------------
with tab_overview:
    col_a, col_b = st.columns([1.65, 1])

    with col_a:
        box = panel("Revenue · by " + BUCKET_LABEL, "Order revenue over time",
                    f"₹ per {BUCKET_LABEL}, {bucket_word(n_buckets)} in range")
        with box:
            if df_buckets.empty:
                empty_state("No orders in this selection",
                            "Widen the date range or clear the city filter.")
            else:
                fig = px.area(df_buckets, x="bucket", y="revenue", markers=True)
                fig.update_traces(
                    line=dict(color=TEAL, width=2),
                    fillcolor="rgba(11,95,85,0.13)",
                    marker=dict(size=5, color=TEAL, line=dict(color="#FFFFFF", width=1)),
                    hovertemplate="%{x}<br><b>₹%{y:,.0f}</b><extra></extra>",
                )
                configure(fig, height=352, value_axis="y", money=True)
                bucket_ticks(fig, df_buckets["bucket"],
                             [bucket_label(b) for b in df_buckets["bucket"]])
                st.plotly_chart(fig, width="stretch",
                                config={"displayModeBar": False})
                if n_buckets > 1:
                    peak = df_buckets.loc[df_buckets["revenue"].idxmax()]
                    trough = df_buckets.loc[df_buckets["revenue"].idxmin()]
                    spread = (
                        (float(peak["revenue"]) - float(trough["revenue"]))
                        / df_buckets["revenue"].mean() * 100
                    )
                    leader = (
                        f"<b>{esc(lead_city)}</b> contributes "
                        f"{100 * lead_city_rev / total_rev:.1f}% of revenue in range."
                        if lead_city else ""
                    )
                    insight(
                        f"Revenue runs {inr_compact(trough['revenue'])} – "
                        f"{inr_compact(peak['revenue'])} per {BUCKET_LABEL} "
                        f"({spread:.1f}% spread), peaking in <b>{esc(bucket_label(peak['bucket']))}</b>. {leader}"
                    )
                else:
                    insight(
                        f"A single {BUCKET_LABEL} in range: "
                        f"<b>{inr(total_rev)}</b> across {total_records:,} lines."
                    )
        sql_box(inline=kpi_sql.strip() + "\n\n" + bucket_sql.strip())

    with col_b:
        box = panel("Markets · top 5", "Cities by revenue",
                    f"share of {inr_compact(total_rev)}")
        with box:
            city_sql = f"""
            SELECT City, ROUND(SUM(Revenue), 2) AS revenue
            FROM orders {WHERE}
            GROUP BY City ORDER BY revenue DESC LIMIT 5
            """
            df_top5 = cached_query(city_sql, tuple(PARAMS))
            if df_top5.empty:
                empty_state("No cities in this selection")
            else:
                df_top5 = df_top5.copy()
                df_top5["share"] = 100 * df_top5["revenue"] / total_rev
                st.markdown(rank_list(df_top5, "City", "revenue", "share"),
                            unsafe_allow_html=True)
                city_count = int(cached_query(
                    f"SELECT COUNT(DISTINCT City) AS n FROM orders {WHERE}",
                    tuple(PARAMS),
                ).iloc[0]["n"])
                top5_share = float(df_top5["share"].sum())
                stat_row([
                    ("Cities in scope", f"{city_count:,}", "cities with orders"),
                    ("Top 5 share", f"{top5_share:.1f}%", f"of {inr_compact(total_rev)}"),
                ])
                verdict = (
                    "concentrated" if top5_share > 55 else
                    "spread evenly" if top5_share < 45 else "balanced"
                )
                city_word = "city" if city_count == 1 else "cities"
                insight(
                    f"The top five cities hold <b>{top5_share:.1f}%</b> of revenue "
                    f"across {city_count} {city_word} in scope — demand is {verdict}."
                )

# ---- Trends ----------------------------------------------------------------
with tab_trend:
    full_trend_sql = f"""
    WITH monthly AS (
      SELECT strftime('%Y-%m', OrderDate) AS month,
             SUM(Revenue) AS revenue, COUNT(*) AS records
      FROM orders {WHERE}
      GROUP BY month
    )
    SELECT month, ROUND(revenue, 2) AS revenue, records,
      ROUND(LAG(revenue) OVER (ORDER BY month), 2) AS prev_month_revenue,
      ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY month))
        / NULLIF(LAG(revenue) OVER (ORDER BY month), 0), 2) AS mom_growth_pct
    FROM monthly ORDER BY month
    """
    df_m = cached_query(full_trend_sql, tuple(PARAMS))

    if df_m.empty:
        empty_state("No monthly trend for this selection",
                    "Widen the date range or clear the city filter.")
    else:
        box = panel("Revenue · monthly", "Revenue and month-over-month change",
                    "₹ per month · dotted line marks the period mean")
        with box:
            fig1 = px.line(df_m, x="month", y="revenue", markers=True)
            fig1.update_traces(
                line=dict(color=TEAL, width=2),
                marker=dict(size=7, color=TEAL, line=dict(color="#FFFFFF", width=1.5)),
                hovertemplate="%{x}<br><b>₹%{y:,.0f}</b><extra></extra>",
            )
            mean_rev = float(df_m["revenue"].mean())
            fig1.add_hline(
                y=mean_rev, line_dash="dot", line_color=AMBER, line_width=1.2,
                annotation_text=f"mean {inr_compact(mean_rev)}",
                annotation_font=dict(family=MONO, size=10.5, color=AMBER),
            )
            configure(fig1, height=330, value_axis="y", money=True)
            bucket_ticks(fig1, df_m["month"], [month_label(m) for m in df_m["month"]])
            st.plotly_chart(fig1, width="stretch",
                            config={"displayModeBar": False})
            insight(
                f"The mean across {len(df_m)} months is <b>{inr_compact(mean_rev)}</b>; "
                f"the widest single move is "
                f"<b>{df_m['mom_growth_pct'].abs().max():.1f}%</b> "
                f"and the series never leaves the "
                f"{inr_compact(df_m['revenue'].min())} – {inr_compact(df_m['revenue'].max())} band."
            )

        box = panel("Momentum · month on month", "Change against the previous month",
                    "per cent, positive in teal · negative in red")
        with box:
            df_mo = df_m.dropna(subset=["mom_growth_pct"]).copy()
            if df_mo.empty:
                empty_state("Not enough months in range",
                            "Pick a range spanning at least two months.")
            else:
                df_mo["direction"] = df_mo["mom_growth_pct"].apply(
                    lambda v: "Up" if v >= 0 else "Down"
                )
                fig2 = px.bar(
                    df_mo, x="month", y="mom_growth_pct", color="direction",
                    color_discrete_map={"Up": POS, "Down": NEG},
                )
                fig2.update_traces(
                    hovertemplate="%{x}<br><b>%{y:+.1f}%</b><extra></extra>",
                )
                configure(
                    fig2, height=270, value_axis="y", pct=True, zero_base=True,
                    legend=True,
                )
                bucket_ticks(fig2, df_mo["month"], [month_label(m) for m in df_mo["month"]])
                fig2.update_layout(
                    legend=dict(title=None, yanchor="bottom", y=1.06, xanchor="right", x=1)
                )
                st.plotly_chart(fig2, width="stretch",
                                config={"displayModeBar": False})
                best = df_mo.loc[df_mo["mom_growth_pct"].idxmax()]
                worst = df_mo.loc[df_mo["mom_growth_pct"].idxmin()]
                insight(
                    f"Largest gain is <b>{esc(month_label(best['month']))} at "
                    f"{best['mom_growth_pct']:+.1f}%</b>; the sharpest fall is "
                    f"<b>{esc(month_label(worst['month']))} at {worst['mom_growth_pct']:+.1f}%</b>. "
                    f"Movement stays inside ±{df_mo['mom_growth_pct'].abs().max():.1f}%, "
                    "so the business is steady rather than seasonal."
                )

        box = panel("Detail · monthly series", "Month, revenue, lines and change",
                    "the table behind both charts")
        with box:
            show = df_m.copy()
            show.insert(0, "Month", show["month"].map(month_label))
            show["Change (%)"] = show["mom_growth_pct"].map(
                lambda v: "—" if pd.isna(v) else f"{v:+.1f}%"
            )
            show = (
                show.drop(columns=["month", "prev_month_revenue", "mom_growth_pct"])
                .rename(columns={
                    "revenue": "Revenue (₹)",
                    "records": "Order lines",
                })[["Month", "Revenue (₹)", "Order lines", "Change (%)"]]
            )
            show["Revenue (₹)"] = show["Revenue (₹)"].map(num)
            st.dataframe(
                show, width="stretch", hide_index=True,
                column_config={
                    "Revenue (₹)": st.column_config.TextColumn(),
                    "Order lines": st.column_config.NumberColumn(format="%.0f"),
                },
            )
        with st.expander("View query · sql/02_monthly_revenue_trend.sql"):
            try:
                st.code(load_sql("02_monthly_revenue_trend.sql").strip(), language="sql")
            except Exception:
                st.code(full_trend_sql.strip(), language="sql")

# ---- Restaurants -----------------------------------------------------------
with tab_rest:
    rest_sql = f"""
    WITH restaurant_stats AS (
      SELECT Restaurant, City, COUNT(*) AS records,
             SUM(Revenue) AS revenue, AVG(Rating) AS avg_rating
      FROM orders {WHERE}
      GROUP BY Restaurant, City
    )
    SELECT Restaurant, City, records,
           ROUND(revenue, 2) AS revenue, ROUND(avg_rating, 2) AS avg_rating
    FROM restaurant_stats ORDER BY revenue DESC LIMIT 10
    """
    df_r = cached_query(rest_sql, tuple(PARAMS))

    if df_r.empty:
        empty_state("No restaurants in this selection",
                    "Widen the date range or clear the city filter.")
    else:
        box = panel("Outlets · top 10 by revenue", "Who earns the most",
                    "₹ revenue, colour is average rating (light = lower, deep = higher)")
        with box:
            fig = px.bar(
                df_r, x="Restaurant", y="revenue", color="avg_rating",
                color_continuous_scale=SEQ_RATING,
                labels={"avg_rating": "Avg rating"},
            )
            fig.update_traces(hovertemplate=(
                "<b>%{x}</b><br>₹%{y:,.0f}<br>rating %{marker.color:.2f}"
                "<extra></extra>"
            ))
            configure(fig, height=400, value_axis="y", money=True,
                      zero_base=True, x_tickangle=-20)
            fig.update_layout(
                coloraxis_colorbar=dict(
                    title=dict(text="rating", font=dict(family=MONO, size=10)),
                    thickness=9, len=0.45, outlinewidth=0, x=1.01,
                    tickfont=dict(family=MONO, size=10, color=MUTED),
                )
            )
            st.plotly_chart(fig, width="stretch",
                            config={"displayModeBar": False})
            top = df_r.iloc[0]
            top10_share = 100 * float(df_r["revenue"].sum()) / total_rev if total_rev else 0
            insight(
                f"<b>{esc(top['Restaurant'])}</b> in {esc(top['City'])} leads at "
                f"<b>{inr(top['revenue'])}</b> — {100 * float(top['revenue']) / total_rev:.1f}% "
                f"of revenue in range, rating {float(top['avg_rating']):.2f}. "
                f"The top 10 outlets together account for {top10_share:.1f}% of the total."
            )

        box = panel("Detail · ranking", "Top 10 restaurants",
                    "ranked by revenue within the current filters")
        with box:
            d = df_r.copy()
            d.insert(0, "Rank", range(1, len(d) + 1))
            d["Share (%)"] = 100 * d["revenue"] / total_rev if total_rev else 0
            d = d.rename(columns={
                "records": "Order lines",
                "revenue": "Revenue (₹)",
                "avg_rating": "Avg rating",
            })[["Rank", "Restaurant", "City", "Order lines", "Revenue (₹)",
                "Share (%)", "Avg rating"]]
            d["Revenue (₹)"] = d["Revenue (₹)"].map(num)
            st.dataframe(
                d, width="stretch", hide_index=True,
                column_config={
                    "Revenue (₹)": st.column_config.TextColumn(),
                    "Order lines": st.column_config.NumberColumn(format="%.0f"),
                    "Share (%)": st.column_config.NumberColumn(format="%.1f"),
                    "Avg rating": st.column_config.NumberColumn(format="%.2f"),
                },
            )
        sql_box(["01_top_restaurants.sql"])

# ---- Dishes ----------------------------------------------------------------
with tab_dish:
    dish_sql = f"""
    WITH item_stats AS (
      SELECT Item, Category, COUNT(*) AS times_ordered,
             AVG(Rating) AS avg_rating, SUM(Revenue) AS revenue
      FROM orders {WHERE}
      GROUP BY Item, Category
    )
    SELECT Item, Category, times_ordered,
           ROUND(avg_rating, 2) AS avg_rating, ROUND(revenue, 2) AS revenue
    FROM item_stats ORDER BY revenue DESC LIMIT 10
    """
    df_p = cached_query(dish_sql, tuple(PARAMS))
    n_items = int(cached_query(
        f"SELECT COUNT(DISTINCT Item) AS n FROM orders {WHERE}", tuple(PARAMS)
    ).iloc[0]["n"])

    if df_p.empty:
        empty_state("No dishes in this selection",
                    "Widen the date range or clear the city filter.")
    else:
        box = panel("Menu · top 10 by revenue", "Which dishes earn the most",
                    f"₹ revenue across {n_items:,} distinct dishes in range")
        with box:
            fig = px.bar(
                df_p, x="revenue", y="Item", orientation="h",
                color="times_ordered", color_continuous_scale=SEQ_VOLUME,
            )
            fig.update_yaxes(autorange="reversed")
            fig.update_traces(hovertemplate=(
                "<b>%{y}</b><br>₹%{x:,.0f}<br>ordered %{marker.color:,.0f} times"
                "<extra></extra>"
            ))
            configure(fig, height=430, value_axis="x", money=True, zero_base=True)
            fig.update_layout(
                coloraxis_colorbar=dict(
                    title=dict(text="lines", font=dict(family=MONO, size=10)),
                    thickness=9, len=0.45, outlinewidth=0, x=1.01,
                    tickfont=dict(family=MONO, size=10, color=MUTED),
                )
            )
            st.plotly_chart(fig, width="stretch",
                            config={"displayModeBar": False})
            top_p = df_p.iloc[0]
            top10_dish = 100 * float(df_p["revenue"].sum()) / total_rev if total_rev else 0
            insight(
                f"<b>{esc(top_p['Item'])}</b> ({esc(top_p['Category'])}) tops the menu at "
                f"<b>{inr(top_p['revenue'])}</b>. The ten best dishes make up "
                f"{top10_dish:.1f}% of revenue out of {n_items:,} distinct dishes — "
                "demand is spread thin rather than carried by a few hits."
            )

        box = panel("Detail · ranking", "Top 10 dishes", "ranked by revenue")
        with box:
            d = df_p.copy()
            d.insert(0, "Rank", range(1, len(d) + 1))
            d["Share (%)"] = 100 * d["revenue"] / total_rev if total_rev else 0
            d = d.rename(columns={
                "times_ordered": "Lines ordered",
                "revenue": "Revenue (₹)",
                "avg_rating": "Avg rating",
            })[["Rank", "Item", "Category", "Lines ordered", "Revenue (₹)",
                "Share (%)", "Avg rating"]]
            d["Revenue (₹)"] = d["Revenue (₹)"].map(num)
            st.dataframe(
                d, width="stretch", hide_index=True,
                column_config={
                    "Revenue (₹)": st.column_config.TextColumn(),
                    "Lines ordered": st.column_config.NumberColumn(format="%.0f"),
                    "Share (%)": st.column_config.NumberColumn(format="%.2f"),
                    "Avg rating": st.column_config.NumberColumn(format="%.2f"),
                },
            )
        sql_box(["03_top_products.sql"])

# ---- Cities ----------------------------------------------------------------
with tab_geo:
    geo_full = f"""
    WITH city_stats AS (
      SELECT City, SUM(Revenue) AS revenue, COUNT(*) AS records,
             COUNT(DISTINCT Restaurant) AS outlets
      FROM orders {WHERE}
      GROUP BY City
    ),
    grand_total AS (SELECT SUM(Revenue) AS t FROM orders {WHERE})
    SELECT c.City, ROUND(c.revenue, 2) AS revenue, c.records, c.outlets,
           ROUND(100.0 * c.revenue / g.t, 2) AS share,
           ROUND(c.revenue / NULLIF(c.records, 0), 2) AS avg_line_value
    FROM city_stats c CROSS JOIN grand_total g ORDER BY c.revenue DESC
    """
    df_g = cached_query(geo_full, tuple(PARAMS) + tuple(PARAMS))

    if df_g.empty:
        empty_state("No city data in this selection")
    else:
        box = panel("Markets · all cities", "Revenue by city",
                    "top 15 shown · leader highlighted")
        with box:
            top15 = df_g.head(15).copy()
            fig = px.bar(top15, x="City", y="revenue")
            fig.update_traces(
                marker_color=[TEAL] + [TEAL_SOFT] * (len(top15) - 1),
                hovertemplate="<b>%{x}</b><br>₹%{y:,.0f}<extra></extra>",
            )
            configure(fig, height=380, value_axis="y", money=True,
                      zero_base=True, x_tickangle=-30)
            st.plotly_chart(fig, width="stretch",
                            config={"displayModeBar": False})
            top5_share = float(df_g.head(5)["share"].sum())
            insight(
                f"<b>{esc(df_g.iloc[0]['City'])}</b> leads at "
                f"<b>{inr(df_g.iloc[0]['revenue'])}</b> "
                f"({float(df_g.iloc[0]['share']):.1f}% of revenue). The top five cities "
                f"hold {top5_share:.1f}% between them across {len(df_g)} cities in scope."
            )

        box = panel("Detail · all cities", "City breakdown",
                    "revenue, share, order lines, outlets and average line value")
        with box:
            d = df_g.copy()
            d.insert(0, "Rank", range(1, len(d) + 1))
            d = d.rename(columns={
                "revenue": "Revenue (₹)",
                "records": "Order lines",
                "outlets": "Outlets",
                "share": "Share (%)",
                "avg_line_value": "Avg line (₹)",
            })[["Rank", "City", "Revenue (₹)", "Share (%)", "Order lines",
                "Outlets", "Avg line (₹)"]]
            d["Revenue (₹)"] = d["Revenue (₹)"].map(num)
            d["Avg line (₹)"] = d["Avg line (₹)"].map(lambda v: num(v, 2))
            st.dataframe(
                d, width="stretch", hide_index=True, height=420,
                column_config={
                    "Revenue (₹)": st.column_config.TextColumn(),
                    "Share (%)": st.column_config.NumberColumn(format="%.2f"),
                    "Order lines": st.column_config.NumberColumn(format="%.0f"),
                    "Outlets": st.column_config.NumberColumn(format="%.0f"),
                    "Avg line (₹)": st.column_config.TextColumn(),
                },
            )
        sql_box(["04_revenue_by_city.sql"])

# ---- Categories and recency -----------------------------------------------
with tab_mix:
    cat_sql = f"""
    SELECT Category, COUNT(*) AS records, ROUND(SUM(Revenue), 2) AS revenue,
           ROUND(AVG(Rating), 2) AS avg_rating
    FROM orders {WHERE}
    GROUP BY Category ORDER BY revenue DESC
    """
    df_c = cached_query(cat_sql, tuple(PARAMS))

    if df_c.empty:
        empty_state("No category data in this selection")
    else:
        n_categories = len(df_c)
        box = panel("Mix · categories", "Where revenue sits in the menu",
                    f"top 8 of {n_categories} categories · ₹ revenue")
        with box:
            top8 = df_c.head(8).copy()
            fig = px.bar(top8, x="revenue", y="Category", orientation="h")
            fig.update_yaxes(autorange="reversed")
            fig.update_traces(
                marker_color=[TEAL] + [TEAL_SOFT] * (len(top8) - 1),
                hovertemplate="<b>%{y}</b><br>₹%{x:,.0f}<extra></extra>",
            )
            configure(fig, height=330, value_axis="x", money=True, zero_base=True)
            st.plotly_chart(fig, width="stretch",
                            config={"displayModeBar": False})
            top8_share = 100 * float(top8["revenue"].sum()) / total_rev if total_rev else 0
            insight(
                f"<b>{esc(df_c.iloc[0]['Category'])}</b> is the largest category at "
                f"<b>{inr(df_c.iloc[0]['revenue'])}</b> "                f"({float(df_c.iloc[0]['revenue']) / total_rev * 100:.1f}% of revenue). "
                f"The top eight make up {top8_share:.1f}% of {n_categories:,} categories — "
                "the mix sits on a long tail."
            )

        veg_sql = f"""
        SELECT VegType, COUNT(*) AS records, ROUND(SUM(Revenue), 2) AS revenue,
               ROUND(AVG(Rating), 2) AS avg_rating
        FROM orders {WHERE}
        GROUP BY VegType ORDER BY revenue DESC
        """
        df_v = cached_query(veg_sql, tuple(PARAMS))

        churn_sql = f"""
        WITH bounds AS (SELECT MAX(date(OrderDate)) AS max_date FROM orders {WHERE}),
        last_seen AS (
          SELECT Restaurant, City, MAX(date(OrderDate)) AS last_date,
                 COUNT(*) AS lifetime_records, ROUND(SUM(Revenue), 2) AS lifetime_revenue
          FROM orders {WHERE}
          GROUP BY Restaurant, City
        )
        SELECT Restaurant, City, last_date,
          CAST(julianday((SELECT max_date FROM bounds)) - julianday(last_date)
               AS INTEGER) AS days_since_last,
          lifetime_records, lifetime_revenue,
          CASE WHEN last_date < date((SELECT max_date FROM bounds), '-90 days')
               THEN 'inactive' ELSE 'active' END AS status
        FROM last_seen ORDER BY days_since_last DESC LIMIT 100
        """
        df_ch = cached_query(churn_sql, tuple(PARAMS) + tuple(PARAMS))

        rate_sql = f"""
        WITH bounds AS (SELECT MAX(date(OrderDate)) AS max_date FROM orders {WHERE}),
        lp AS (
          SELECT Restaurant, City, MAX(date(OrderDate)) AS last_date
          FROM orders {WHERE} GROUP BY Restaurant, City
        )
        SELECT COUNT(*) AS n,
          SUM(CASE WHEN last_date < date((SELECT max_date FROM bounds), '-90 days')
                   THEN 1 ELSE 0 END) AS inactive,
          (SELECT max_date FROM bounds) AS max_date
        FROM lp
        """
        rate = cached_query(rate_sql, tuple(PARAMS) + tuple(PARAMS)).iloc[0]
        n_outlets = int(rate["n"] or 0)
        n_inactive = int(rate["inactive"] or 0)
        inactive_rate = (100 * n_inactive / n_outlets) if n_outlets else 0

        box = panel("Mix · veg and non-veg", "Vegetarian and non-vegetarian split",
                    "share of revenue in the current filters")
        with box:
            if df_v.empty:
                empty_state("No veg split for this selection")
            else:
                total_v = float(df_v["revenue"].sum()) or 1
                segments = []
                palette = {"Veg": TEAL, "Non-Veg": AMBER}
                base = 0.0
                fig = go.Figure()
                for _, row in df_v.iterrows():
                    name = str(row["VegType"])
                    value = float(row["revenue"])
                    fig.add_trace(go.Bar(
                        x=[value], y=[""], orientation="h", base=base,
                        name=name, marker_color=palette.get(name, MUTED),
                        text=f"{name}  {100 * value / total_v:.1f}%",
                        textposition="inside", textfont=dict(
                            family=MONO, size=12, color="#FFFFFF"),
                        hovertemplate=f"{name}<br>₹%{{x:,.0f}}<extra></extra>",
                    ))
                    base += value
                fig.update_layout(
                    barmode="stack", bargap=0.35,
                    showlegend=False, height=110,
                    margin=dict(l=4, r=4, t=10, b=4),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family=SANS, size=12),
                    hoverlabel=dict(bgcolor=INK, bordercolor=INK, font=dict(family=MONO,
                                     size=11.5, color="#FFFFFF")),
                )
                fig.update_xaxes(showgrid=False, visible=False)
                fig.update_yaxes(showgrid=False, visible=False)
                st.plotly_chart(fig, width="stretch",
                                config={"displayModeBar": False})
                veg_row = df_v[df_v["VegType"].str.lower().str.startswith("veg")] \
                    if not df_v.empty else pd.DataFrame()
                veg_share = float(veg_row["revenue"].iloc[0]) / total_v * 100 if len(veg_row) else 0
                insight(
                    f"Vegetarian lines bring <b>{veg_share:.1f}%</b> of revenue "
                    f"({inr_compact(veg_row['revenue'].iloc[0]) if len(veg_row) else '--'}) "
                    f"against non-veg {100 - veg_share:.1f}%, on "
                    f"{int(df_v['records'].sum()):,} order lines."
                )

        box = panel("Retention · outlet recency", "How fresh is the outlet base",
                    "inactive = no order in the 90 days before the last order in range")
        with box:
            stat_row([
                ("Inactive outlets", f"{inactive_rate:.1f}%",
                 f"{n_inactive:,} of {n_outlets:,} outlets"),
                ("Days since last order", f"{int(df_ch['days_since_last'].max()) if len(df_ch) else 0}",
                 "longest gap in the current scope"),
                ("Outlets tracked", f"{n_outlets:,}", "distinct restaurant–city pairs"),
            ])
            st.markdown(
                f'<div class="insight"><span class="ins-tag">INSIGHT</span>'
                f"<b>{inactive_rate:.1f}%</b> of outlets "
                f"({n_inactive:,} of {n_outlets:,}) have not taken an order in the "
                f"90 days before {pd.to_datetime(rate['max_date']).strftime('%d %b %Y')}. "
                f"Ten most dormant outlets are listed below.</div>",
                unsafe_allow_html=True,
            )
            show = df_ch.head(50).rename(columns={
                "Restaurant": "Outlet",
                "City": "City",
                "last_date": "Last order",
                "days_since_last": "Days idle",
                "lifetime_records": "Lifetime lines",
                "lifetime_revenue": "Lifetime revenue (₹)",
                "status": "Status",
            })
            show["Lifetime revenue (₹)"] = show["Lifetime revenue (₹)"].map(num)
            st.dataframe(
                show, width="stretch", hide_index=True, height=360,
                column_config={
                    "Days idle": st.column_config.NumberColumn(format="%.0f"),
                    "Lifetime lines": st.column_config.NumberColumn(format="%.0f"),
                    "Lifetime revenue (₹)": st.column_config.TextColumn(),
                },
            )

        c1, c2 = st.columns(2)
        with c1:
            sql_box(["05_repeat_vs_onetime.sql"])
        with c2:
            sql_box(["06_churn.sql"])

# ---- SQL explorer ----------------------------------------------------------
with tab_sql:
    box = panel("Ad hoc · read only", "Run your own query",
                "SELECT only · 200 row cap · parameterised dashboard queries never take text input")
    with box:
        user_sql = st.text_area(
            "Query",
            value=(
                "SELECT City, COUNT(*) AS lines, ROUND(SUM(Revenue), 2) AS revenue\n"
                "FROM orders\n"
                "GROUP BY City\n"
                "ORDER BY revenue DESC\n"
                "LIMIT 10"
            ),
            height=150,
        )
        run = st.button("Run query", type="primary")

        if run:
            cleaned = user_sql.strip().lstrip(";").strip()
            first_word = cleaned.split(None, 1)[0].upper() if cleaned.split() else ""
            blocked = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
                       "REPLACE", "ATTACH", "DETACH"]
            if first_word != "SELECT":
                st.error("Start with SELECT. Only read queries are allowed here.")
            elif any(word in cleaned.upper() for word in blocked):
                st.error("Write operations are blocked. SELECT only.")
            else:
                try:
                    limited = cleaned.rstrip(";")
                    if "LIMIT" not in cleaned.upper():
                        limited += " LIMIT 200"
                    df_u = run_query(limited, (), db_path=DB_PATH).head(200)
                    st.success(f"{len(df_u):,} rows returned (capped at 200).")
                    st.dataframe(df_u, width="stretch", height=340)
                except Exception as e:
                    st.error(f"Query failed: {e}")

    box = panel("Intake · CSV preview", "Check a file before it goes near the database",
                "parsed in memory for this session · the database is never written to")
    with box:
        up = st.file_uploader("CSV with Restaurant, Item, City, OrderDate, Price",
                              type=["csv"])
        if up is None:
            st.caption("No file selected.")
        else:
            try:
                pdf = pd.read_csv(up, encoding="unicode_escape", nrows=5000)
                pdf.columns = [c.strip() for c in pdf.columns]
                if "Price" not in pdf.columns:
                    st.error("The file needs at least a Price column.")
                else:
                    pdf["Revenue"] = pd.to_numeric(pdf["Price"], errors="coerce")
                    stat_row([
                        ("Rows", f"{len(pdf):,}", "preview capped at 5,000"),
                        ("Revenue", inr(pdf["Revenue"].sum()), "sum of Price in the preview"),
                        ("Columns", f"{len(pdf.columns):,}", "as parsed from the file"),
                    ])
                    st.dataframe(pdf.head(20), width="stretch", height=320)
            except Exception as e:
                st.error(f"Could not read the CSV: {e}")

# ----------------------------------------------------------------------------
# Footer
# ----------------------------------------------------------------------------

st.markdown(
    '<div class="footnote">'
    "<b>Definitions.</b> Revenue is the item price on an order line; the file carries no "
    "delivery fees, discounts or costs. One row is one order line, so order totals are line "
    "counts. Inactive outlet means no record in the 90 days before the latest order date in "
    "the selection. Rows missing restaurant, item or city, and rows with non-positive price, "
    "were removed before analysis. Source: Swiggy orders file in data/. "
    f"<b>Coverage.</b> {int(profile['lines']):,} lines · "
    f"{int(profile['outlets']):,} outlets · {int(profile['cities']):} cities · "
    f"{pd.to_datetime(profile['min_d']).strftime('%d %b %Y')} – "
    f"{pd.to_datetime(profile['max_d']).strftime('%d %b %Y')}."
    "</div>"
    '<div class="foot-credit">Streamlit · pandas · SQLite · Plotly — '
    "queries in sql/, build in src/data_prep.py</div>",
    unsafe_allow_html=True,
)
