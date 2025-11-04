import json
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, List, Literal, Optional, Tuple

import gradio as gr
import pandas as pd
import plotly.express as px
from sqlalchemy import bindparam, text

from .logger import engine

# ----------------------------
# Constants and types
# ----------------------------

Period = Literal["Hour", "Day", "Week", "Month"]
GroupBy = Literal["None", "route", "user_agent", "status", "rerank", "lang", "client"]
PERIOD_FREQ = {"Hour": "H", "Day": "D", "Week": "W", "Month": "M"}
PARAM_KEYS = ("rerank", "lang")

@dataclass(frozen=True)
class QueryFilters:
    start: datetime
    end: datetime
    routes: List[str]
    statuses: List[int]
    ua_include: Optional[str]
    ua_exclude: Optional[str]
    rerank_filter: Literal["any", "true", "false", "unset"]
    langs_filter: List[str]
    period: Period
    group_by: GroupBy


# ----------------------------
# Time helpers
# ----------------------------

def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc).replace(microsecond=0)

def to_naive_utc(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc).replace(tzinfo=None)

def normalize_dt(val: Any) -> datetime:
    if isinstance(val, datetime):
        return to_naive_utc(val)
    if isinstance(val, (int, float)):
        s = float(val)
        # allow ns, us, ms heuristics
        if s > 1e14:      # ns
            s /= 1e9
        elif s > 1e11:    # us
            s /= 1e6
        elif s > 1e10:    # ms
            s /= 1e3
        return datetime.utcfromtimestamp(s)
    dt = pd.to_datetime(val, utc=True, errors="coerce")
    if pd.isna(dt):
        raise ValueError("Invalid datetime")
    return dt.tz_convert(None).to_pydatetime()


# ----------------------------
# Data access
# ----------------------------

def _build_sql_and_params(
    start: datetime,
    end: datetime,
    routes: List[str],
    statuses: List[int],
    ua_include: Optional[str],
) -> Tuple[Any, dict]:
    base = """
        SELECT timestamp, route, user_agent, status, parameters
        FROM requests
        WHERE timestamp BETWEEN :start AND :end
    """

    params: dict = {"start": start, "end": end}
    clauses: List[str] = []

    if routes:
        clauses.append("route IN :routes")
    if statuses:
        clauses.append("status IN :statuses")
    if ua_include:
        clauses.append("LOWER(user_agent) LIKE :ua_inc")
        params["ua_inc"] = f"%{ua_include.lower()}%"

    if clauses:
        base += " AND " + " AND ".join(clauses)

    stmt = text(base)
    if routes:
        stmt = stmt.bindparams(bindparam("routes", expanding=True))
        params["routes"] = list(routes)
    if statuses:
        stmt = stmt.bindparams(bindparam("statuses", expanding=True))
        params["statuses"] = list(statuses)

    return stmt, params

def load_requests_df(
    start: datetime,
    end: datetime,
    routes: List[str],
    statuses: List[int],
    ua_include: Optional[str],
    ua_exclude: Optional[str],
) -> pd.DataFrame:
    stmt, params = _build_sql_and_params(start, end, routes, statuses, ua_include)
    with engine.connect() as conn:
        df = pd.read_sql(stmt, conn, params=params, parse_dates=["timestamp"])

    if df.empty:
        return df

    df["status"] = df["status"].astype(int)

    # Exclude UA via pandas for simple contains
    if ua_exclude:
        mask = ~df["user_agent"].fillna("").str.contains(ua_exclude, case=False, na=False)
        df = df[mask]

    return df


# ----------------------------
# Transforms
# ----------------------------

def _extract_params_col(s: pd.Series) -> pd.DataFrame:
    """
    Parse JSON in the 'parameters' column and extract 'rerank' and 'lang'.
    Returns a DataFrame with columns ['rerank','lang'] normalized.
    """
    def parse_one(x: Any) -> dict:
        try:
            d = json.loads(x) if isinstance(x, str) and x else {}
        except Exception:
            d = {}
        rerank = str(d.get("rerank")).strip().lower() if "rerank" in d else ""
        if rerank == "" or rerank not in ("true", "false"):
            rerank = "unset"
        lang = d.get("lang")
        lang_norm = str(lang).strip() if lang not in (None, "") else "all"
        return {"rerank": rerank, "lang": lang_norm}

    parsed = s.map(parse_one)
    return pd.DataFrame(list(parsed))

def apply_param_filters(df: pd.DataFrame, rerank_filter: str, langs_filter: List[str]) -> pd.DataFrame:
    if df.empty:
        return df
    if "parameters" in df.columns:
        extracted = _extract_params_col(df["parameters"])
        df = pd.concat([df.reset_index(drop=True), extracted], axis=1)
    else:
        df["rerank"], df["lang"] = "unset", "all"

    if rerank_filter in ("true", "false", "unset"):
        df = df[df["rerank"] == rerank_filter]
    if langs_filter:
        df = df[df["lang"].isin(langs_filter)]
    return df

def aggregate_requests(df: pd.DataFrame, period: Period, group_by: GroupBy) -> pd.DataFrame:
    if df.empty:
        return df
    freq = PERIOD_FREQ[period]
    df = df.copy()

    # Derived grouping: browser vs API based on UA
    if group_by == "client":
        ua = df.get("user_agent", pd.Series(index=df.index, dtype=object)).fillna("")
        is_browser = ua.str.contains("mozilla", case=False, na=False)
        df["client"] = is_browser.map({True: "browser", False: "api"})

    df = df.set_index("timestamp")

    if group_by == "None":
        out = df.groupby(pd.Grouper(freq=freq)).size().reset_index(name="requests")
    else:
        out = df.groupby([pd.Grouper(freq=freq), group_by]).size().reset_index(name="requests")

    out = out.rename(columns={"timestamp": "bucket"})
    return out


# ----------------------------
# Charts
# ----------------------------

def empty_ts(group_by: GroupBy):
    if group_by == "None":
        base = pd.DataFrame({"bucket": [], "requests": []})
        return px.line(base, x="bucket", y="requests", title="No data", markers=True)
    base = pd.DataFrame({"bucket": [], "requests": [], group_by: []})
    return px.line(base, x="bucket", y="requests", color=group_by, title="No data", markers=True)

def empty_bar(group_by: GroupBy):
    if group_by == "None":
        base = pd.DataFrame({"category": [], "requests": []})
        return px.bar(base, x="category", y="requests", title="No data")
    base = pd.DataFrame({group_by: [], "requests": []})
    return px.bar(base, x=group_by, y="requests", title="No data")

def make_charts(agg: pd.DataFrame, group_by: GroupBy):
    if agg.empty:
        return empty_ts(group_by), empty_bar(group_by), pd.DataFrame()

    if group_by == "None":
        fig_ts = px.line(agg, x="bucket", y="requests", markers=True, title="Requests over time")
        totals = agg[["requests"]].sum().to_frame(name="requests")
        totals["category"] = "All"
        totals = totals[["category", "requests"]]
        fig_bar = px.bar(totals, x="category", y="requests", title="Total requests")
    else:
        fig_ts = px.line(
            agg, x="bucket", y="requests", color=group_by, markers=True,
            title=f"Requests over time by {group_by}"
        )
        totals = agg.groupby(group_by)["requests"].sum().sort_values(ascending=False).reset_index()
        fig_bar = px.bar(totals, x=group_by, y="requests", title=f"Requests by {group_by}")
    return fig_ts, fig_bar, totals


# ----------------------------
# Choice helpers with caching
# ----------------------------

@lru_cache(maxsize=1)
def route_choices(limit: int = 500) -> List[str]:
    q = text("""
        SELECT DISTINCT route AS v
        FROM requests
        WHERE route IS NOT NULL AND route != ''
        ORDER BY 1
        LIMIT :limit
    """)
    with engine.connect() as conn:
        df = pd.read_sql(q, conn, params={"limit": limit})
    return df["v"].dropna().astype(str).tolist() if not df.empty else []

@lru_cache(maxsize=1)
def status_choices(limit: int = 500) -> List[int]:
    q = text("""
        SELECT DISTINCT status AS v
        FROM requests
        WHERE status IS NOT NULL
        ORDER BY 1
        LIMIT :limit
    """)
    with engine.connect() as conn:
        df = pd.read_sql(q, conn, params={"limit": limit})
    return sorted([int(x) for x in df["v"].tolist()]) if not df.empty else []

@lru_cache(maxsize=1)
def lang_choices(sample: int = 2000) -> List[str]:
    q = text("""
        SELECT parameters
        FROM requests
        WHERE parameters IS NOT NULL AND parameters != ''
        ORDER BY timestamp DESC
        LIMIT :sample
    """)
    with engine.connect() as conn:
        df = pd.read_sql(q, conn, params={"sample": sample})
    vals: set[str] = set()
    for s in df.get("parameters", []):
        try:
            d = json.loads(s)
            v = d.get("lang")
            if v is not None and str(v).strip() != "":
                vals.add(str(v))
        except Exception:
            continue
    return sorted(vals)

# ----------------------------
# Orchestration
# ----------------------------

def run_query(filters: QueryFilters):
    # Normalize and validate time
    s = normalize_dt(filters.start)
    e = normalize_dt(filters.end)
    if s > e:
        s, e = e, s

    df = load_requests_df(
        start=s,
        end=e,
        routes=filters.routes or [],
        statuses=filters.statuses or [],
        ua_include=filters.ua_include or "",
        ua_exclude=filters.ua_exclude or "",
    )

    df = apply_param_filters(df, filters.rerank_filter or "any", filters.langs_filter or [])
    agg = aggregate_requests(df, filters.period, filters.group_by)
    fig_ts, fig_bar, totals = make_charts(agg, filters.group_by)
    return fig_ts, fig_bar, totals


# ----------------------------
# Public Gradio builder
# ----------------------------

def build_analytics_app():
    now = utc_now()
    default_start = now - pd.Timedelta(days=7)

    with gr.Blocks(title="API Analytics") as demo:
        gr.Markdown("## API Analytics")

        with gr.Row():
            start_dt = gr.DateTime(label="Start UTC", value=default_start, interactive=True)
            end_dt = gr.DateTime(label="End UTC", value=now, interactive=True)
            period = gr.Dropdown(choices=list(PERIOD_FREQ.keys()), value="Day", label="Time bucket")
            group_by = gr.Dropdown(
                choices=["None", "route", "user_agent", "status", "rerank", "lang", "client"],
                value="None",
                label="Group by",
            )

        with gr.Row():
            route_dd = gr.CheckboxGroup(choices=route_choices(), label="Filter routes", value=[])
            status_dd = gr.CheckboxGroup(choices=[str(s) for s in status_choices()], label="Filter status codes", value=[])
            ua_inc = gr.Textbox(label="User agent contains", placeholder="curl, python-requests, chrome")
            ua_exc = gr.Textbox(label="User agent does NOT contain", placeholder="bot, uptime, healthcheck")

        with gr.Row():
            rerank_dd = gr.Dropdown(choices=["any", "true", "false", "unset"], value="any", label="Filter rerank")
            langs_dd = gr.Dropdown(choices=lang_choices(), value=[], multiselect=True, label="Filter lang")

        btn = gr.Button("Refresh", variant="primary")

        ts_plot = gr.Plot(label="Requests over time")
        bar_plot = gr.Plot(label="Totals")
        table = gr.Dataframe(label="Totals table", interactive=False)

        def _run(
            start, end, period_v, group_by_v, routes, statuses, ua_include, ua_exclude, rerank_filter, langs_filter
        ):
            f = QueryFilters(
                start=start,
                end=end,
                period=period_v,
                group_by=group_by_v,
                routes=routes or [],
                statuses=[int(x) for x in statuses] if statuses else [],
                ua_include=ua_include,
                ua_exclude=ua_exclude,
                rerank_filter=rerank_filter or "any",
                langs_filter=langs_filter or [],
            )
            return run_query(f)

        inputs = [start_dt, end_dt, period, group_by, route_dd, status_dd, ua_inc, ua_exc, rerank_dd, langs_dd]

        btn.click(fn=_run, inputs=inputs, outputs=[ts_plot, bar_plot, table], queue=False)

        # Live updates on change without queueing
        gr.on(triggers=[x.change for x in inputs], fn=_run, inputs=inputs, outputs=[ts_plot, bar_plot, table], queue=False)

    return demo
