from typing import Dict, Any
from config import INFLATION_BY_YEAR, REGIONAL_INDEX

def infer_inflation_factor(execution_year: int) -> float:
    # If year is in table, use it; else assume 3% per missing year relative to 2023
    if execution_year in INFLATION_BY_YEAR:
        return INFLATION_BY_YEAR[execution_year]
    # simple fallback
    base_year = 2023
    years = max(0, base_year - int(execution_year))
    return (1.03) ** years

def apply_cost_scaling(base_project: dict,
                       scaling_factors: Dict[str, float],
                       soft_costs: Dict[str, float]) -> Dict[str, Any]:
    # Pull WBS components
    wbs_keys = ["civil_cost","mechanical_cost","electrical_cost","automation_cost"]
    base_wbs = {k: float(base_project.get(k, 0.0)) for k in wbs_keys}

    # If the estimator didn't supply inflation factor, we can derive from year
    if "inflation_factor" not in scaling_factors or scaling_factors["inflation_factor"] <= 0:
        scaling_factors["inflation_factor"] = infer_inflation_factor(int(base_project["execution_year"]))

    total_scaled_wbs = 0.0
    scaled_wbs = {}
    factor = (
        scaling_factors["capacity_scale_factor"] *
        scaling_factors["regional_index_factor"] *
        scaling_factors["inflation_factor"] *
        scaling_factors["complexity_modifier"]
    )
    for k, v in base_wbs.items():
        scaled_wbs[k] = round(v * factor, 2)
        total_scaled_wbs += scaled_wbs[k]

    engineering = round(total_scaled_wbs * float(soft_costs["engineering_pct"]), 2)
    contingency = round(total_scaled_wbs * float(soft_costs["contingency_pct"]), 2)
    total = round(total_scaled_wbs + engineering + contingency, 2)

    return {
        "scaled_wbs_costs": scaled_wbs,
        "engineering_cost": engineering,
        "contingency_cost": contingency,
        "total_estimated_cost": total,
        "applied_factor": round(factor, 4)
    }
