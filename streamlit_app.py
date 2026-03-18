import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

from retriever import Retriever
from estimator_agent import EstimatorAgent
from scaler import apply_cost_scaling
from reviewer import review
from report_writer import write_summary
from config import REGIONAL_INDEX, REGION_COUNTRIES

# Demo mode: AI link disabled to force deterministic fallback.
OPENAI_API_KEY = None


# ---------- UI CONFIG ----------
st.set_page_config(
    page_title="AI Project Cost Estimator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------- HELPERS ----------
def fmt_millions(x: float) -> str:
    try:
        return f"${x/1_000_000:,.2f}M"
    except Exception:
        return "-"


def wbs_core_keys() -> list[str]:
    return ["civil_cost", "mechanical_cost", "electrical_cost", "automation_cost"]


def capacity_settings_for_type(dataframe: pd.DataFrame, selected_type: str):
    subset = dataframe[dataframe["project_type"] == selected_type]["capacity"].dropna().astype(float)
    if subset.empty:
        return 100, 2000, 400, 50

    raw_min = float(subset.min())
    raw_max = float(subset.max())
    span = max(1.0, raw_max - raw_min)

    cap_min = int(max(50, np.floor((raw_min - 0.10 * span) / 25) * 25))
    cap_max = int(min(3000, np.ceil((raw_max + 0.10 * span) / 25) * 25))
    if cap_max <= cap_min:
        cap_max = cap_min + 100

    if span <= 300:
        step = 10
    elif span <= 700:
        step = 25
    else:
        step = 50

    default = int(np.clip(np.median(subset), cap_min, cap_max))
    default = int(round(default / step) * step)
    default = min(max(default, cap_min), cap_max)

    return cap_min, cap_max, default, step


def inject_theme(mode: str):
    is_dark = mode == "Dark"

    if is_dark:
        bg = "#0b111b"
        surface = "#111827"
        surface_2 = "#0f172a"
        text = "#e5e7eb"
        muted = "#9ca3af"
        border = "rgba(148, 163, 184, 0.20)"
        accent = "#5ea4ff"
        accent_soft = "rgba(94, 164, 255, 0.16)"
        shadow = "0 12px 36px rgba(2, 6, 23, 0.48)"
    else:
        bg = "#f4f7fb"
        surface = "#ffffff"
        surface_2 = "#f8fafc"
        text = "#0f172a"
        muted = "#475569"
        border = "rgba(15, 23, 42, 0.10)"
        accent = "#1f6feb"
        accent_soft = "rgba(31, 111, 235, 0.12)"
        shadow = "0 12px 30px rgba(15, 23, 42, 0.08)"

    css = f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

      :root {{
        --bg: {bg};
        --surface: {surface};
        --surface-2: {surface_2};
        --text: {text};
        --muted: {muted};
        --border: {border};
        --accent: {accent};
        --accent-soft: {accent_soft};
        --shadow: {shadow};
      }}

      html, body, [class*="css"]  {{
        font-family: 'Manrope', sans-serif;
      }}

      .stApp {{
        background: radial-gradient(circle at 0% 0%, var(--accent-soft) 0%, transparent 30%), var(--bg);
        color: var(--text);
      }}

      [data-testid="stSidebar"] {{
        border-right: 1px solid var(--border);
        background: var(--surface-2);
      }}

      .main .block-container {{
        padding-top: 1.4rem;
        padding-bottom: 2rem;
      }}

      .hero {{
        background: linear-gradient(120deg, var(--surface), var(--surface-2));
        border: 1px solid var(--border);
        border-radius: 18px;
        box-shadow: var(--shadow);
        padding: 1.1rem 1.2rem;
        margin-bottom: 1rem;
      }}

      .hero h1 {{
        margin: 0;
        font-size: 1.45rem;
        font-weight: 800;
        line-height: 1.25;
        color: var(--text);
      }}

      .hero p {{
        margin: .45rem 0 0;
        color: var(--muted);
        font-size: 0.93rem;
      }}

      .kpi-card {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 14px;
        box-shadow: var(--shadow);
        padding: .85rem .9rem;
        min-height: 100px;
        transition: transform .15s ease, box-shadow .15s ease;
      }}

      .kpi-card:hover {{
        transform: translateY(-1px);
        box-shadow: 0 14px 32px rgba(15, 23, 42, 0.12);
      }}

      .kpi-label {{
        color: var(--muted);
        font-size: .76rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: .04em;
      }}

      .kpi-value {{
        color: var(--text);
        font-size: 1.18rem;
        font-weight: 800;
        margin-top: .2rem;
      }}

      .kpi-sub {{
        color: var(--muted);
        font-size: .8rem;
        margin-top: .25rem;
      }}

      .panel-title {{
        margin: .2rem 0 .45rem;
        color: var(--text);
        font-size: 1rem;
        font-weight: 750;
      }}

      .confidence-card {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: .8rem .9rem;
      }}

      .confidence-label {{
        color: var(--muted);
        font-size: .76rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: .04em;
      }}

      .confidence-value {{
        color: var(--text);
        font-size: 1.28rem;
        font-weight: 800;
        margin-top: .2rem;
      }}

      .summary-card {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 14px;
        box-shadow: var(--shadow);
        padding: .9rem 1rem;
      }}

      .summary-card p {{
        margin: 0;
        color: var(--text);
      }}

      .detailed-summary {{
        margin-top: .15rem;
      }}

      .detailed-summary h1 {{
        font-size: 1.04rem;
        margin: .2rem 0 .45rem;
        font-weight: 760;
        color: var(--text);
      }}

      .detailed-summary h2 {{
        font-size: .95rem;
        margin: .55rem 0 .35rem;
        font-weight: 700;
        color: var(--text);
      }}

      .detailed-summary h3 {{
        font-size: .88rem;
        margin: .45rem 0 .25rem;
        font-weight: 680;
        color: var(--text);
      }}

      .detailed-summary p,
      .detailed-summary li {{
        font-size: .84rem;
        line-height: 1.4;
      }}

      .detailed-summary table {{
        font-size: .8rem;
      }}

      .detailed-summary th,
      .detailed-summary td {{
        padding: .24rem .4rem;
      }}

      .section-space {{
        margin-top: .2rem;
      }}

      .stDataFrame, [data-testid="stTable"], div[data-testid="stMetric"] {{
        border: 1px solid var(--border);
        border-radius: 12px;
      }}

      .stDownloadButton button,
      .stButton button {{
        border-radius: 10px;
        border: 1px solid var(--border);
      }}

      .stDownloadButton button:hover,
      .stButton button:hover {{
        border-color: var(--accent);
        color: var(--accent);
      }}

      h2, h3 {{
        letter-spacing: -0.01em;
      }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def kpi_card(label: str, value: str, sub: str):
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def confidence_card(value: str, sub: str):
    st.markdown(
        f"""
        <div class="confidence-card">
            <div class="confidence-label">Confidence Level</div>
            <div class="confidence-value">{value}</div>
            <div class="kpi-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def executive_summary_snapshot(request: dict, scaled: dict, reviewer_out: dict, reasoning: list[str]):
    total_cost = scaled["total_estimated_cost"]
    top_reasoning = [r for r in reasoning if isinstance(r, str) and r.strip()][:3]

    st.markdown('<div class="summary-card">', unsafe_allow_html=True)
    c1, c2 = st.columns([1.0, 1.3], gap="large")
    with c1:
        st.write(f"**Project Type:** {request['project_type']}")
        st.write(f"**Region/Country:** {request['region']} / {request['country']}")
        st.write(f"**Capacity:** {request['capacity']:,}")
        st.write(f"**Execution Year:** {request['execution_year']}")
        st.write(f"**Estimated CAPEX:** {fmt_millions(total_cost)}")
    with c2:
        notes = reviewer_out.get("notes", [])[:3]
        if notes:
            st.write("**Reviewer Notes**")
            for note in notes:
                st.write(f"- {note}")
        if top_reasoning:
            st.write("**Model Assumptions**")
            for item in top_reasoning:
                st.write(f"- {item}")
    st.markdown("</div>", unsafe_allow_html=True)


def build_plot_theme(mode: str) -> dict:
    if mode == "Dark":
        return {
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "font_color": "#e5e7eb",
            "gridcolor": "rgba(148, 163, 184, 0.22)",
            "accent": "#5ea4ff",
            "colors": ["#5ea4ff", "#18b8a4", "#f59e0b", "#fb7185", "#8b5cf6", "#f97316"],
        }
    return {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font_color": "#0f172a",
        "gridcolor": "rgba(15, 23, 42, 0.12)",
        "accent": "#1f6feb",
        "colors": ["#1f6feb", "#0f766e", "#d97706", "#e11d48", "#7c3aed", "#ea580c"],
    }


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


# ---------- DATA ----------
DATA_PATH = "data/synthetic_capex_projects_optionA.csv"
df = load_data(DATA_PATH)
project_types = sorted(df["project_type"].unique())
regions = sorted(df["region"].unique())
year_min = int(df["execution_year"].min())
year_max = int(df["execution_year"].max())


# ---------- SIDEBAR ----------
st.sidebar.markdown("### Estimation Controls")
if hasattr(st.sidebar, "segmented_control"):
    appearance = st.sidebar.segmented_control(
        "Theme",
        options=["Light", "Dark"],
        default="Light",
    )
else:
    appearance = st.sidebar.radio("Theme", options=["Light", "Dark"], horizontal=True)
inject_theme(appearance)
plot_theme = build_plot_theme(appearance)

project_type = st.sidebar.selectbox("Project Type", project_types)
region = st.sidebar.selectbox("Region", regions)
countries = REGION_COUNTRIES.get(
    region,
    sorted(df[df["region"] == region]["country"].dropna().unique().tolist()),
)
country = st.sidebar.selectbox("Country", countries)
cap_min, cap_max, cap_default, cap_step = capacity_settings_for_type(df, project_type)
capacity = st.sidebar.slider("Capacity / Throughput", cap_min, cap_max, cap_default, step=cap_step)
execution_year_default = min(max(2022, year_min), year_max)
execution_year = st.sidebar.slider("Execution Year", year_min, year_max, execution_year_default)
compare_toggle = st.sidebar.toggle("Benchmark vs. median similar projects", value=True)
run_estimate = st.sidebar.button("Run Estimate", type="primary", use_container_width=True)


# ---------- HERO ----------
st.markdown(
    """
    <div class="hero">
      <h1>AI Project Cost Estimator</h1>
      <p>Executive-grade CAPEX estimation for manufacturing projects with AI-assisted scaling, benchmark comparators, and risk-aware confidence checks.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------- ESTIMATION ----------
if "estimate_payload" not in st.session_state:
    st.session_state["estimate_payload"] = None

if run_estimate:
    request = {
        "project_type": project_type,
        "region": region,
        "country": country,
        "capacity": capacity,
        "execution_year": execution_year,
    }

    retriever = Retriever(DATA_PATH, REGIONAL_INDEX)
    similar_df = retriever.find_similar(request, top_k=5)

    if similar_df.empty:
        st.error("No comparable projects were found for this request. Try broader inputs.")
        st.stop()

    base_row = similar_df.iloc[0].to_dict()

    spinner_msg = (
        "Generating AI-informed scaling factors..."
        if OPENAI_API_KEY
        else "OPENAI_API_KEY missing, using deterministic fallback heuristics..."
    )

    with st.spinner(spinner_msg):
        estimator = EstimatorAgent()
        estimate_json = estimator.infer_factors(similar_df, request)

    scaling_factors = estimate_json["scaling_factors"]
    soft_costs = estimate_json["soft_costs"]
    reasoning = estimate_json.get("reasoning", [])
    estimate_mode = estimate_json.get("meta", {}).get("mode", "ai")

    scaled = apply_cost_scaling(base_row, scaling_factors, soft_costs)
    wbs = scaled["scaled_wbs_costs"]

    reviewer_out = review(similar_df.to_dict(orient="records"), scaled, scaling_factors)
    report_md = write_summary(request, base_row, scaling_factors, scaled, reviewer_out, reasoning)

    st.session_state["estimate_payload"] = {
        "request": request,
        "similar_df": similar_df,
        "estimate_json": estimate_json,
        "scaled": scaled,
        "reviewer_out": reviewer_out,
        "report_md": report_md,
        "project_type": project_type,
        "country": country,
        "plot_theme": plot_theme,
    }

payload = st.session_state.get("estimate_payload")

if payload:
    request = payload["request"]
    similar_df = payload["similar_df"]
    estimate_json = payload["estimate_json"]
    scaled = payload["scaled"]
    reviewer_out = payload["reviewer_out"]
    report_md = payload["report_md"]
    project_type = payload["project_type"]
    country = payload["country"]
    wbs = scaled["scaled_wbs_costs"]
    estimate_mode = estimate_json.get("meta", {}).get("mode", "ai")

    # ---------- KPI ROW ----------
    total_cost = scaled["total_estimated_cost"]
    engineering_share = (scaled["engineering_cost"] / total_cost * 100) if total_cost else 0
    contingency_share = (scaled["contingency_cost"] / total_cost * 100) if total_cost else 0

    confidence = reviewer_out.get("confidence", "-unknown-")
    similar_count = len(similar_df)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Total Estimated CAPEX", fmt_millions(total_cost), f"{project_type} in {country}")
    with c2:
        kpi_card("Confidence", str(confidence).title(), f"Based on {similar_count} comparable projects")
    with c3:
        kpi_card("Engineering", f"{engineering_share:,.1f}%", "Share of total estimate")
    with c4:
        kpi_card("Contingency", f"{contingency_share:,.1f}%", "Risk reserve allocation")

    if estimate_mode != "ai":
        st.warning("AI estimator unavailable for this run. Deterministic fallback heuristics were used.")
    else:
        st.success("Estimate generated using AI-assisted scaling + deterministic cost engine.")

    # ---------- MAIN GRID ----------
    left, right = st.columns([1.15, 1.0], gap="large")

    with left:
        st.markdown('<div class="panel-title">Top Comparable Historical Projects</div>', unsafe_allow_html=True)
        show_cols = [
            "project_id",
            "project_name",
            "region",
            "country",
            "capacity",
            "execution_year",
            "total_cost_usd",
        ]
        df_show = similar_df[show_cols].copy()
        df_show["total_cost_usd"] = df_show["total_cost_usd"].apply(fmt_millions)
        st.dataframe(df_show, width="stretch", hide_index=True)

        st.markdown('<div class="panel-title">Estimated WBS Cost Breakdown</div>', unsafe_allow_html=True)
        tb = pd.DataFrame(
            {
                "Category": [
                    "Civil",
                    "Mechanical",
                    "Electrical",
                    "Automation",
                    "Engineering",
                    "Contingency",
                    "TOTAL",
                ],
                "Cost": [
                    wbs["civil_cost"],
                    wbs["mechanical_cost"],
                    wbs["electrical_cost"],
                    wbs["automation_cost"],
                    scaled["engineering_cost"],
                    scaled["contingency_cost"],
                    scaled["total_estimated_cost"],
                ],
            }
        )
        tb["Cost (USD, M)"] = tb["Cost"].apply(lambda x: f"{x/1_000_000:,.2f}")
        st.table(tb[["Category", "Cost (USD, M)"]])

    with right:
        wbs_df = pd.DataFrame(
            [
                ["Civil", wbs["civil_cost"]],
                ["Mechanical", wbs["mechanical_cost"]],
                ["Electrical", wbs["electrical_cost"]],
                ["Automation", wbs["automation_cost"]],
                ["Engineering", scaled["engineering_cost"]],
                ["Contingency", scaled["contingency_cost"]],
            ],
            columns=["Category", "Cost"],
        )
        wbs_df["Cost (USD, M)"] = wbs_df["Cost"] / 1_000_000

        st.markdown('<div class="panel-title">Cost Breakdown by Category (USD, Millions)</div>', unsafe_allow_html=True)
        bar_fig = px.bar(
            wbs_df,
            x="Category",
            y="Cost (USD, M)",
            text="Cost (USD, M)",
            color="Category",
            color_discrete_sequence=plot_theme["colors"],
        )
        bar_fig.update_traces(texttemplate="%{text:,.2f}", textposition="outside")
        bar_fig.update_layout(
            yaxis_title="USD (Millions)",
            xaxis_title=None,
            showlegend=False,
            margin=dict(t=18, l=8, r=8, b=8),
            paper_bgcolor=plot_theme["paper_bgcolor"],
            plot_bgcolor=plot_theme["plot_bgcolor"],
            font=dict(color=plot_theme["font_color"]),
        )
        bar_fig.update_yaxes(gridcolor=plot_theme["gridcolor"])
        st.plotly_chart(bar_fig, width="stretch")

        st.markdown('<div class="panel-title">Cost Composition Share</div>', unsafe_allow_html=True)
        pie_fig = px.pie(
            wbs_df,
            names="Category",
            values="Cost",
            hole=0.54,
            color="Category",
            color_discrete_sequence=plot_theme["colors"],
        )
        pie_fig.update_traces(textposition="inside", textinfo="percent")
        pie_fig.update_layout(
            margin=dict(t=18, l=8, r=8, b=8),
            paper_bgcolor=plot_theme["paper_bgcolor"],
            plot_bgcolor=plot_theme["plot_bgcolor"],
            font=dict(color=plot_theme["font_color"]),
            legend_title_text=None,
        )
        st.plotly_chart(pie_fig, width="stretch")

    # ---------- BENCHMARK ----------
    if compare_toggle:
        st.markdown('<div class="panel-title section-space">Benchmark: Median of Similar Projects (Core WBS)</div>', unsafe_allow_html=True)
        med_core = {}
        for k in wbs_core_keys():
            med_core[k] = float(np.median(similar_df[k].astype(float)))

        comp_df = pd.DataFrame(
            {
                "Category": ["Civil", "Mechanical", "Electrical", "Automation"],
                "Estimated (USD, M)": [
                    wbs["civil_cost"] / 1_000_000,
                    wbs["mechanical_cost"] / 1_000_000,
                    wbs["electrical_cost"] / 1_000_000,
                    wbs["automation_cost"] / 1_000_000,
                ],
                "Median of Similars (USD, M)": [
                    med_core["civil_cost"] / 1_000_000,
                    med_core["mechanical_cost"] / 1_000_000,
                    med_core["electrical_cost"] / 1_000_000,
                    med_core["automation_cost"] / 1_000_000,
                ],
            }
        )
        long_df = comp_df.melt(id_vars="Category", var_name="Series", value_name="USD (Millions)")
        cmp_fig = px.bar(
            long_df,
            x="Category",
            y="USD (Millions)",
            color="Series",
            barmode="group",
            color_discrete_sequence=[plot_theme["accent"], "#94a3b8"],
        )
        cmp_fig.update_layout(
            yaxis_title="USD (Millions)",
            xaxis_title=None,
            margin=dict(t=20, l=8, r=8, b=8),
            paper_bgcolor=plot_theme["paper_bgcolor"],
            plot_bgcolor=plot_theme["plot_bgcolor"],
            font=dict(color=plot_theme["font_color"]),
            legend_title_text=None,
        )
        cmp_fig.update_yaxes(gridcolor=plot_theme["gridcolor"])
        st.plotly_chart(cmp_fig, width="stretch")

    # ---------- REVIEW + SUMMARY ----------
    st.markdown('<div class="panel-title section-space">Review & Confidence</div>', unsafe_allow_html=True)
    col_a, col_b = st.columns([1.0, 1.0], gap="large")

    with col_a:
        confidence_card(
            str(reviewer_out.get("confidence", "Unknown")).title(),
            f"Based on {len(similar_df)} comparable projects",
        )
        notes = reviewer_out.get("notes", [])
        if notes:
            st.caption("Notes")
            for note in notes:
                st.write(f"- {note}")

    with col_b:
        flags = reviewer_out.get("flags", [])
        if flags:
            st.error("Issues detected")
            for flag in flags:
                st.write(f"- {flag}")
        else:
            st.success("No critical review flags were detected.")

    with st.expander("Model Factors & Reasoning", expanded=False):
        st.json(estimate_json)

    st.markdown('<div class="panel-title section-space">Executive Summary</div>', unsafe_allow_html=True)
    executive_summary_snapshot(
        request=request,
        scaled=scaled,
        reviewer_out=reviewer_out,
        reasoning=estimate_json.get("reasoning", []),
    )

    with st.expander("Full Detailed Markdown Summary", expanded=False):
        st.markdown('<div class="detailed-summary">', unsafe_allow_html=True)
        st.markdown(report_md)
        st.markdown("</div>", unsafe_allow_html=True)

    st.download_button(
        label="Download Summary (Markdown)",
        data=report_md,
        file_name="capex_estimate_summary.md",
        mime="text/markdown",
        use_container_width=False,
    )

else:
    st.info("Configure project parameters in the sidebar, then click Run Estimate.")
    if not OPENAI_API_KEY:
        st.caption(
            "Set OPENAI_API_KEY to enable AI factor inference. Without it, deterministic fallback heuristics are used."
        )

    # A compact empty-state dashboard for first load.
    e1, e2, e3, e4 = st.columns(4)
    with e1:
        kpi_card("Total Estimated CAPEX", "-", "Run an estimate to populate")
    with e2:
        kpi_card("Confidence", "-", "Awaiting model review")
    with e3:
        kpi_card("Engineering", "-", "Share of total estimate")
    with e4:
        kpi_card("Contingency", "-", "Risk reserve allocation")
