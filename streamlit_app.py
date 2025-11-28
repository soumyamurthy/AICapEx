import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

from retriever import Retriever
from estimator_agent import EstimatorAgent
from scaler import apply_cost_scaling
from reviewer import review
from report_writer import write_summary
from config import REGIONAL_INDEX

# ---------- UI CONFIG ----------
st.set_page_config(page_title="AI CapEx Estimator", layout="wide")
st.title("🏗️ AI-Driven CapEx Estimator (Project-Level)")

# ---------- HELPERS ----------
def fmt_millions(x: float) -> str:
    try:
        return f"${x/1_000_000:,.2f}M"
    except Exception:
        return "-"

def wbs_core_keys():
    return ["civil_cost", "mechanical_cost", "electrical_cost", "automation_cost"]

# ---------- LOAD DATA ----------
@st.cache_data
def load_data(path):
    return pd.read_csv(path)

DATA_PATH = "data/synthetic_capex_projects_optionA.csv"
df = load_data(DATA_PATH)
project_types = sorted(df["project_type"].unique())
regions = sorted(df["region"].unique())

# ---------- SIDEBAR INPUT PANEL ----------
st.sidebar.header("Project Input Parameters")
project_type = st.sidebar.selectbox("Project Type", project_types)
region = st.sidebar.selectbox("Region", regions)
capacity = st.sidebar.slider("Capacity / Throughput", 100, 2000, 400, step=50)
execution_year = st.sidebar.slider("Execution Year", 2015, 2024, 2022)
compare_toggle = st.sidebar.toggle("Compare with Median of Similar Projects (core WBS)", value=False)

if st.sidebar.button("Run Estimate"):
    request = {
        "project_type": project_type,
        "region": region,
        "capacity": capacity,
        "execution_year": execution_year
    }

    # ---------- RETRIEVE SIMILARS ----------
    retriever = Retriever(DATA_PATH, REGIONAL_INDEX)
    similar_df = retriever.find_similar(request, top_k=5)

    st.subheader("🔍 Top Comparable Historical Projects")
    show_cols = ["project_id","project_name","region","capacity","execution_year","total_cost_usd"]
    df_show = similar_df[show_cols].copy()
    df_show["total_cost_usd"] = df_show["total_cost_usd"].apply(fmt_millions)
    st.dataframe(df_show, use_container_width=True)

    base_row = similar_df.iloc[0].to_dict()

    # ---------- LLM ESTIMATOR ----------
    with st.spinner("Generating scaling factors using LLM reasoning..."):
        estimator = EstimatorAgent()
        estimate_json = estimator.infer_factors(similar_df, request)

    scaling_factors = estimate_json["scaling_factors"]
    soft_costs = estimate_json["soft_costs"]
    reasoning = estimate_json.get("reasoning", [])

    st.subheader("⚙️ Scaling Factors (LLM-Inferred)")
    st.json(estimate_json)

    # ---------- APPLY COST SCALING ----------
    scaled = apply_cost_scaling(base_row, scaling_factors, soft_costs)
    wbs = scaled["scaled_wbs_costs"]

    # ---------- WBS TABLE (Millions) ----------
    st.subheader("📊 Estimated WBS Cost Breakdown")
    tb = pd.DataFrame({
        "Category": ["Civil","Mechanical","Electrical","Automation","Engineering","Contingency","TOTAL"],
        "Cost": [
            wbs["civil_cost"],
            wbs["mechanical_cost"],
            wbs["electrical_cost"],
            wbs["automation_cost"],
            scaled["engineering_cost"],
            scaled["contingency_cost"],
            scaled["total_estimated_cost"],
        ],
    })
    tb["Cost (USD, M)"] = tb["Cost"].apply(lambda x: f"{x/1_000_000:,.2f}")
    st.table(tb[["Category","Cost (USD, M)"]])

    # ---------- BAR CHART (Millions) ----------
    wbs_df = pd.DataFrame([
        ["Civil", wbs["civil_cost"]],
        ["Mechanical", wbs["mechanical_cost"]],
        ["Electrical", wbs["electrical_cost"]],
        ["Automation", wbs["automation_cost"]],
        ["Engineering", scaled["engineering_cost"]],
        ["Contingency", scaled["contingency_cost"]],
    ], columns=["Category","Cost"])
    wbs_df["Cost (USD, M)"] = wbs_df["Cost"] / 1_000_000

    st.subheader("📈 Cost Breakdown by Category (USD, Millions)")
    bar_fig = px.bar(
        wbs_df,
        x="Category",
        y="Cost (USD, M)",
        text="Cost (USD, M)",
    )
    bar_fig.update_traces(texttemplate="%{text:,.2f}", textposition="outside")
    bar_fig.update_layout(yaxis_title="USD (Millions)", xaxis_title=None, showlegend=False, margin=dict(t=40))
    st.plotly_chart(bar_fig, use_container_width=True)

    # ---------- DONUT CHART ----------
    st.subheader("🍩 Cost Composition Share")
    pie_fig = px.pie(
        wbs_df,
        names="Category",
        values="Cost",
        hole=0.4,
    )
    pie_fig.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(pie_fig, use_container_width=True)

    # ---------- OPTIONAL: MEDIAN COMPARATOR (core WBS only) ----------
    if compare_toggle:
        st.subheader("📊 Comparator: Median of Similar Projects (Core WBS only)")
        # Compute median only for core WBS categories present in dataset
        med_core = {}
        for k in wbs_core_keys():
            med_core[k] = float(np.median(similar_df[k].astype(float)))
        comp_df = pd.DataFrame({
            "Category": ["Civil","Mechanical","Electrical","Automation"],
            "Estimated (USD, M)": [
                wbs["civil_cost"]/1_000_000,
                wbs["mechanical_cost"]/1_000_000,
                wbs["electrical_cost"]/1_000_000,
                wbs["automation_cost"]/1_000_000,
            ],
            "Median of Similars (USD, M)": [
                med_core["civil_cost"]/1_000_000,
                med_core["mechanical_cost"]/1_000_000,
                med_core["electrical_cost"]/1_000_000,
                med_core["automation_cost"]/1_000_000,
            ]
        })
        long_df = comp_df.melt(id_vars="Category", var_name="Series", value_name="USD (Millions)")
        cmp_fig = px.bar(long_df, x="Category", y="USD (Millions)", color="Series", barmode="group")
        cmp_fig.update_layout(yaxis_title="USD (Millions)", xaxis_title=None, margin=dict(t=40))
        st.plotly_chart(cmp_fig, use_container_width=True)

    # ---------- REVIEW ----------
    reviewer_out = review(similar_df.to_dict(orient="records"), scaled, scaling_factors)
    st.subheader("🔎 Review & Confidence")
    st.write(f"**Confidence Level:** {reviewer_out['confidence']}")
    if reviewer_out["notes"]:
        st.write("**Notes:**")
        for n in reviewer_out["notes"]:
            st.write(f"- {n}")
    if reviewer_out["flags"]:
        st.error("⚠️ Issues Detected:")
        for f in reviewer_out["flags"]:
            st.write(f"- {f}")

    # ---------- EXEC SUMMARY + DOWNLOAD ----------
    st.subheader("📝 Executive Summary (Markdown)")
    report_md = write_summary(request, base_row, scaling_factors, scaled, reviewer_out, reasoning)
    # Replace $ with $Xm in the markdown totals for readability (optional)
    st.markdown(report_md)

    st.download_button(
        label="⬇️ Download Summary as Markdown",
        data=report_md,
        file_name="capex_estimate_summary.md",
        mime="text/markdown"
    )

else:
    st.info("Configure project parameters in the sidebar and click **Run Estimate**.")
