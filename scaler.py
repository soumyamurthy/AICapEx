from typing import Dict, Any
from config import INFLATION_BY_YEAR, REGIONAL_INDEX

def infer_inflation_factor(execution_year: int) -> float:
    # If year is in table, use it directly.
    if execution_year in INFLATION_BY_YEAR:
        return INFLATION_BY_YEAR[execution_year]

    # Extrapolate from nearest known year at 3%/year.
    known_years = sorted(INFLATION_BY_YEAR.keys())
    if not known_years:
        return 1.0

    year = int(execution_year)
    min_year = known_years[0]
    max_year = known_years[-1]
    min_factor = float(INFLATION_BY_YEAR[min_year])
    max_factor = float(INFLATION_BY_YEAR[max_year])

    if year < min_year:
        return min_factor * ((1.03) ** (min_year - year))

    if year > max_year:
        return max_factor / ((1.03) ** (year - max_year))

    # Missing year inside known range: use nearest lower known year and project.
    lower_years = [y for y in known_years if y < year]
    anchor = max(lower_years) if lower_years else min_year
    anchor_factor = float(INFLATION_BY_YEAR[anchor])
    return anchor_factor / ((1.03) ** (year - anchor))

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
