import argparse
import pandas as pd
from retriever import Retriever
from estimator_agent import EstimatorAgent
from scaler import apply_cost_scaling
from reviewer import review
from report_writer import write_summary
from config import REGIONAL_INDEX

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/synthetic_capex_projects_optionA.csv",
                    help="Path to project-level CSV")
    ap.add_argument("--project_type", required=False, default="Filling Line")
    ap.add_argument("--region", required=False, default="Europe")
    ap.add_argument("--capacity", type=int, required=False, default=400)
    ap.add_argument("--execution_year", type=int, required=False, default=2022)
    ap.add_argument("--k", type=int, default=5, help="Top-K similar projects")
    ap.add_argument("--print_topk", action="store_true")
    return ap.parse_args()

def main():
    args = parse_args()

    # 1) Build request
    request = {
        "project_type": args.project_type,
        "region": args.region,
        "capacity": args.capacity,
        "execution_year": args.execution_year
    }

    # 2) Retrieve similars
    retriever = Retriever(args.data, REGIONAL_INDEX)
    similar_df = retriever.find_similar(request, top_k=args.k)
    if args.print_topk:
        print("\n--- Top-K Similar Projects ---")
        print(similar_df[["project_id","project_type","region","capacity","execution_year","total_cost_usd"]])

    base_row = similar_df.iloc[0].to_dict()

    # 3) Estimator Agent (LLM) → scaling factors & soft costs
    estimator = EstimatorAgent()
    estimate_json = estimator.infer_factors(similar_df, request)
    scaling_factors = estimate_json["scaling_factors"]
    soft_costs = estimate_json["soft_costs"]
    reasoning = estimate_json.get("reasoning", [])

    # 4) Deterministic scaler
    scaled = apply_cost_scaling(base_row, scaling_factors, soft_costs)

    # 5) Reviewer
    reviewer_out = review(similar_df.to_dict(orient="records"), scaled, scaling_factors)

    # 6) Report
    report = write_summary(request, base_row, scaling_factors, scaled, reviewer_out, reasoning)
    print("\n" + report + "\n")

if __name__ == "__main__":
    main()
