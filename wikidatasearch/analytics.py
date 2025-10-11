# analytics.py
import json
from datetime import datetime, timezone
from typing import Any, List, Optional, Tuple

import gradio as gr
import pandas as pd
import plotly.express as px
from sqlalchemy import bindparam, text

from .logger import engine

def _choices(col: str, limit: int = 500) -> List[str]:
    q = f"""
        SELECT DISTINCT {col} AS v
        FROM requests
        WHERE {col} IS NOT NULL AND {col} != ''
        ORDER BY 1
        LIMIT {limit}
    """
    with engine.connect() as conn:
        df = pd.read_sql(q, conn)
    return df["v"].dropna().astype(str).tolist() if not df.empty else []

def _param_choices(key: str, sample: int = 2000) -> List[str]:
    # Pull latest N parameter blobs, parse JSON, collect distinct values for a key
    q = f"""
        SELECT parameters
        FROM requests
        WHERE parameters IS NOT NULL AND parameters != ''
        ORDER BY timestamp DESC
        LIMIT {sample}
    """
    with engine.connect() as conn:
        df = pd.read_sql(q, conn)
    vals = set()
    for s in df.get("parameters", []):
        try:
            d = json.loads(s)
            v = d.get(key)
            if v is not None and str(v).strip() != "":
                vals.add(str(v))
        except Exception:
            pass
    return sorted(vals)

def _to_naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt

def _normalize_dt(val: Any) -> datetime:
    if isinstance(val, datetime):
        return _to_naive_utc(val)
    if isinstance(val, (int, float)):
        s = float(val)
        if s > 1e14:      # ns
            s /= 1e9
        elif s > 1e11:    # us
            s /= 1e6
        elif s > 1e10:    # ms
            s /= 1e3
        return _to_naive_utc(datetime.utcfromtimestamp(s))
    dt = pd.to_datetime(val, utc=True, errors="coerce")
    if pd.isna(dt):
        return datetime.utcnow()
    try:
        dt = dt.tz_convert(None)
    except Exception:
        dt = dt.tz_localize(None)
    return dt.to_pydatetime()

def _build_sql_and_params(
    start: datetime,
    end: datetime,
    routes: List[str],
    statuses: List[int],
    ua_include: Optional[str],
    ua_exclude: Optional[str],
) -> Tuple[Any, dict]:
    base = """
        SELECT timestamp, route, user_agent, status, parameters
        FROM requests
        WHERE timestamp BETWEEN :start AND :end
    """
    params = {"start": start, "end": end}
    clauses = []

    if routes:
        clauses.append("route IN :routes")
    if statuses:
        clauses.append("status IN :statuses")
    # UA include/exclude are cheaper in SQL LIKE, but we can also do it in pandas.
    # Do include in SQL, exclude in pandas to keep syntax simple.
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

def _load_data(
    start: datetime,
    end: datetime,
    routes: List[str],
    statuses: List[int],
    ua_include: Optional[str],
    ua_exclude: Optional[str],
) -> pd.DataFrame:
    stmt, params = _build_sql_and_params(start, end, routes, statuses, ua_include, ua_exclude)
    with engine.connect() as conn:
        df = pd.read_sql(stmt, conn, params=params, parse_dates=["timestamp"])
    if df.empty:
        return df

    df["status"] = df["status"].astype(int)

    # UA exclude in pandas
    if ua_exclude:
        mask = ~df["user_agent"].fillna("").str.contains(ua_exclude, case=False, na=False)
        df = df[mask]

    # Extract params: rerank, lang
    def _extract(row: str):
        try:
            d = json.loads(row or "{}")
        except Exception:
            d = {}
        rerank = d.get("rerank")
        # normalize to "true"/"false"
        if rerank is None or str(rerank).strip() == "":
            rerank_norm = "false"
        else:
            rerank_norm = str(rerank).lower()
        lang = d.get("lang")
        lang_norm = str(lang) if lang not in (None, "") else "all"
        return pd.Series({"rerank": rerank_norm, "lang": lang_norm})

    params_extracted = df["parameters"].apply(_extract)
    df = pd.concat([df, params_extracted], axis=1)
    return df

def _filter_params(
    df: pd.DataFrame,
    rerank_filter: str,
    langs_filter: List[str],
) -> pd.DataFrame:
    if df.empty:
        return df
    if rerank_filter in ("true", "false", "unset"):
        df = df[df["rerank"] == rerank_filter]
    if langs_filter:
        df = df[df["lang"].isin(langs_filter)]
    return df

def _aggregate(df: pd.DataFrame, period: str, group_by: str) -> pd.DataFrame:
    if df.empty:
        return df

    # Use Grouper to avoid Period conversion issues
    freq_map = {"Hour": "H", "Day": "D", "Week": "W", "Month": "M"}  # month-end
    freq = freq_map.get(period, "D")

    if group_by == "None":
        agg = (
            df.set_index("timestamp")
              .groupby(pd.Grouper(freq=freq))
              .size()
              .reset_index(name="requests")
        )
    else:
        agg = (
            df.set_index("timestamp")
              .groupby([pd.Grouper(freq=freq), group_by])
              .size()
              .reset_index(name="requests")
        )

    agg = agg.rename(columns={"timestamp": "bucket"})
    return agg

def _empty_fig_ts(group_by: str):
    if group_by == "None":
        base = pd.DataFrame({"bucket": [], "requests": []})
        return px.line(base, x="bucket", y="requests", title="No data", markers=True)
    base = pd.DataFrame({"bucket": [], "requests": [], group_by: []})
    return px.line(base, x="bucket", y="requests", color=group_by, title="No data", markers=True)

def _empty_fig_bar(group_by: str):
    if group_by == "None":
        base = pd.DataFrame({"category": [], "requests": []})
        return px.bar(base, x="category", y="requests", title="No data")
    base = pd.DataFrame({group_by: [], "requests": []})
    return px.bar(base, x=group_by, y="requests", title="No data")

def _make_charts(agg: pd.DataFrame, group_by: str):
    if agg.empty:
        return _empty_fig_ts(group_by), _empty_fig_bar(group_by), pd.DataFrame()

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

def _run_query(
    start,
    end,
    period,
    group_by,
    routes,
    statuses,
    ua_include,
    ua_exclude,
    rerank_filter,
    langs_filter,
):
    s = _normalize_dt(start)
    e = _normalize_dt(end)
    if s > e:
        s, e = e, s
    statuses = [int(x) for x in statuses] if statuses else []

    df = _load_data(s, e, routes or [], statuses, ua_include or "", ua_exclude or "")
    df = _filter_params(df, rerank_filter or "any", langs_filter or [])

    agg = _aggregate(df, period, group_by)
    fig_ts, fig_bar, totals = _make_charts(agg, group_by)
    return fig_ts, fig_bar, totals

# ----------------------------
# Public builder
# ----------------------------

def build_analytics_app():
    now = datetime.utcnow().replace(microsecond=0)
    default_start = now - pd.Timedelta(days=7)

    route_choices = _choices("route")
    status_choices = sorted([int(s) for s in _choices("status") if str(s).isdigit()])
    lang_choices = _param_choices("lang")
    rerank_choices = ["any", "true", "false", "unset"]

    with gr.Blocks(title="API Analytics") as demo:
        gr.Markdown("## API Analytics")

        with gr.Row():
            start_dt = gr.DateTime(label="Start UTC", value=default_start, interactive=True)
            end_dt = gr.DateTime(label="End UTC", value=now, interactive=True)
            period = gr.Dropdown(choices=["Hour", "Day", "Week", "Month"], value="Day", label="Time bucket")
            group_by = gr.Dropdown(
                choices=["None", "route", "user_agent", "status", "rerank", "lang"],
                value="None",
                label="Group by",
            )

        with gr.Row():
            route_dd = gr.CheckboxGroup(choices=route_choices, label="Filter routes", value=[])
            status_dd = gr.CheckboxGroup(choices=[str(s) for s in status_choices], label="Filter status codes", value=[])
            ua_inc = gr.Textbox(label="User agent contains", placeholder="curl, python-requests, chrome")
            ua_exc = gr.Textbox(label="User agent does NOT contain", placeholder="bot, uptime, healthcheck")

        with gr.Row():
            rerank_dd = gr.Dropdown(choices=rerank_choices, value="any", label="Filter rerank")
            langs_dd = gr.Dropdown(choices=lang_choices, value=[], multiselect=True, label="Filter lang")

        btn = gr.Button("Refresh", variant="primary")

        ts_plot = gr.Plot(label="Requests over time")
        bar_plot = gr.Plot(label="Totals")
        table = gr.Dataframe(label="Totals table", interactive=False)

        inputs = [
            start_dt, end_dt, period, group_by,
            route_dd, status_dd, ua_inc, ua_exc, rerank_dd, langs_dd
        ]

        btn.click(
            fn=_run_query,
            inputs=inputs,
            outputs=[ts_plot, bar_plot, table],
            queue=False,
        )

        gr.on(
            triggers=[x.change for x in inputs],
            fn=_run_query,
            inputs=inputs,
            outputs=[ts_plot, bar_plot, table],
            queue=False,
        )

    return demo
