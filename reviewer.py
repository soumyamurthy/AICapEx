from typing import Dict, Any, List, Tuple
import statistics as stats
from config import COMPLEXITY_MIN_MAX

def _ratio(a, b):
    return (a / b) if (b and b != 0) else 0.0

def review(similar_rows: List[dict],
           scaled_result: Dict[str, Any],
           scaling_factors: Dict[str, float]) -> Dict[str, Any]:
    flags = []
    notes = []

    # Check complexity modifier range
    cmin, cmax = COMPLEXITY_MIN_MAX
    cm = scaling_factors.get("complexity_modifier", 1.0)
    if not (cmin <= cm <= cmax):
        flags.append(f"Complexity modifier {cm} outside expected range {cmin}-{cmax}.")

    # Compare total vs. historical totals (rough sniff test)
    hist_totals = [float(r.get("total_cost_usd", 0.0)) for r in similar_rows if float(r.get("total_cost_usd",0.0)) > 0]
    if len(hist_totals) >= 3:
        med = stats.median(hist_totals)
        ratio = _ratio(scaled_result["total_estimated_cost"], med)
        if ratio > 2.0:
            flags.append("Total estimate >2x median of similars.")
        elif ratio < 0.5:
            flags.append("Total estimate <0.5x median of similars.")
        notes.append(f"Median of similars: {med:,.0f}; Estimate/Median ratio: {ratio:.2f}")

    confidence = "High"
    if flags:
        confidence = "Medium" if len(flags) == 1 else "Low"

    return {
        "flags": flags,
        "notes": notes,
        "confidence": confidence
    }
