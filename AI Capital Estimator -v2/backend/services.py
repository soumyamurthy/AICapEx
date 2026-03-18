"""Business logic for capex portfolio analysis."""

from __future__ import annotations

from datetime import date
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from .models import Project, Risk, Vendor


def calculate_schedule_variance(project: Project) -> float:
    """Return schedule variance in days (positive means late)."""
    if not project.actual_end_date:
        return 0.0
    planned = project.planned_end_date
    actual = project.actual_end_date
    return (actual - planned).days


def calculate_cost_overrun_pct(project: Project) -> float:
    if project.budget_usd <= 0:
        return 0.0
    return (project.actual_cost_usd - project.budget_usd) / project.budget_usd


def is_high_risk(project: Project, vendors: List[Vendor]) -> bool:
    # Risk criteria based on vendor reliability and cost/schedule
    vendor = next((v for v in vendors if v.vendor_id == project.vendor_id), None)
    # Fallback heuristic: use risk_score
    if project.risk_score > 0.75:
        return True
    if vendor:
        if vendor.reliability_score < 0.7 and project.percent_complete < 0.5:
            return True
    if (project.actual_cost_usd > 0.9 * project.budget_usd) and project.percent_complete < 0.7:
        return True
    return False


def predict_risks(project: Project, vendors: List[Vendor]) -> Dict[str, Any]:
    """Return simple prediction flags for a project."""
    flags: Dict[str, Any] = {}
    vendor = next((v for v in vendors if v.vendor_id == project.vendor_id), None)
    if vendor:
        flags["vendor_reliability"] = vendor.reliability_score
        flags["high_delay_risk"] = vendor.reliability_score < 0.7 and project.percent_complete < 0.5
    else:
        flags["vendor_reliability"] = None
        flags["high_delay_risk"] = False

    flags["cost_overrun_risk"] = (
        project.actual_cost_usd > 0.9 * project.budget_usd and project.percent_complete < 0.7
    )
    flags["schedule_variance_days"] = calculate_schedule_variance(project)
    flags["cost_overrun_pct"] = calculate_cost_overrun_pct(project)
    return flags


def build_portfolio_summary(projects: List[Project], risks: List[Risk], vendors: List[Vendor]) -> Dict[str, Any]:
    total_budget = sum(p.budget_usd for p in projects)
    total_actual = sum(p.actual_cost_usd for p in projects)
    delayed = [p for p in projects if p.status == "Delayed"]
    completed = [p for p in projects if p.status == "Completed"]
    avg_overrun = 0.0
    if projects:
        avg_overrun = sum(calculate_cost_overrun_pct(p) for p in projects) / len(projects)
    high_risk_projects = [p for p in projects if is_high_risk(p, vendors)]

    top_risky = sorted(projects, key=lambda p: p.risk_score, reverse=True)[:5]

    return {
        "total_budget": total_budget,
        "total_actual_cost": total_actual,
        "percent_delayed": (len(delayed) / len(projects)) * 100 if projects else 0,
        "avg_cost_overrun_pct": avg_overrun,
        "high_risk_count": len(high_risk_projects),
        "top_risky_projects": [p.project_id for p in top_risky],
        "total_projects": len(projects),
        "total_risks": len(risks),
        "total_vendors": len(vendors),
    }


def format_project_for_api(project: Project, vendors: List[Vendor]) -> Dict[str, Any]:
    data = project.model_dump()
    data.update(predict_risks(project, vendors))
    return data


@lru_cache(maxsize=1)
def load_data(path: str) -> Dict[str, Any]:
    import json

    from pathlib import Path

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Data file not found: {path}")

    payload = json.loads(p.read_text())
    # Convert back to models
    payload["projects"] = [Project.model_validate(p) for p in payload.get("projects", [])]
    payload["risks"] = [Risk.model_validate(r) for r in payload.get("risks", [])]
    payload["vendors"] = [Vendor.model_validate(v) for v in payload.get("vendors", [])]
    return payload
