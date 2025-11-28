from tabulate import tabulate

def write_summary(request: dict,
                  base_project: dict,
                  scaling_factors: dict,
                  scaled_result: dict,
                  reviewer_out: dict,
                  reasoning_bullets: list) -> str:
    lines = []
    lines.append("# AI-Generated CapEx Estimate\n")
    lines.append("## Request\n")
    lines.append(tabulate([[request["project_type"], request["region"], request["capacity"], request["execution_year"]]],
                          headers=["Project Type","Region","Capacity","Year"], tablefmt="github"))
    lines.append("\n## Selected Base Comparable")
    lines.append(tabulate([[base_project["project_id"], base_project["project_name"], base_project["region"],
                            base_project["capacity"], base_project["execution_year"]]],
                          headers=["ID","Name","Region","Capacity","Year"], tablefmt="github"))
    lines.append("\n## Scaling Factors (LLM-derived)")
    sf_tab = [[scaling_factors["capacity_scale_factor"],
               scaling_factors["regional_index_factor"],
               scaling_factors["inflation_factor"],
               scaling_factors["complexity_modifier"]]]
    lines.append(tabulate(sf_tab, headers=["Capacity","Region","Inflation","Complexity"], tablefmt="github"))
    lines.append("\n## Result (Deterministic Math)")
    wbs = scaled_result["scaled_wbs_costs"]
    result_rows = [
        ["Civil", f'{wbs["civil_cost"]:,.0f}'],
        ["Mechanical", f'{wbs["mechanical_cost"]:,.0f}'],
        ["Electrical", f'{wbs["electrical_cost"]:,.0f}'],
        ["Automation", f'{wbs["automation_cost"]:,.0f}'],
        ["Engineering", f'{scaled_result["engineering_cost"]:,.0f}'],
        ["Contingency", f'{scaled_result["contingency_cost"]:,.0f}'],
        ["**Total**", f'{scaled_result["total_estimated_cost"]:,.0f}']
    ]
    lines.append(tabulate(result_rows, headers=["Category","Cost (USD)"], tablefmt="github"))
    lines.append(f"\nApplied overall factor: **{scaled_result['applied_factor']}**")

    if reasoning_bullets:
        lines.append("\n## Assumptions & Reasoning (LLM)")
        for r in reasoning_bullets:
            lines.append(f"- {r}")

    lines.append("\n## Reviewer")
    lines.append(f"- Confidence: **{reviewer_out['confidence']}**")
    if reviewer_out["notes"]:
        for n in reviewer_out["notes"]:
            lines.append(f"- Note: {n}")
    if reviewer_out["flags"]:
        for f in reviewer_out["flags"]:
            lines.append(f"- ⚠️ {f}")

    return "\n".join(lines)
