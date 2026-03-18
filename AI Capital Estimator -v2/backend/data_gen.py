"""Synthetic data generator for capex projects."""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List

from .models import Project, Risk, Vendor


ASSET_TYPES = [
    "Packaging Line",
    "Filling Line",
    "Warehouse Automation",
    "Utilities",
    "Material Handling",
    "Quality Lab",
    "Safety Upgrade",
]

RISK_TYPES = ["Supplier Delay", "Cost Inflation", "Scope Change", "Technical Issue"]
LOCATIONS = ["USA - Chicago", "Germany - Frankfurt", "China - Shanghai", "Mexico - Monterrey", "India - Pune"]


def _rand_date(base: date, delta_days: int) -> date:
    return base + timedelta(days=random.randint(0, delta_days))


def _clamp(x: float, minv: float, maxv: float) -> float:
    return max(minv, min(maxv, x))


def generate_synthetic_data(
    num_projects: int = 80,
    num_vendors: int = 15,
    output_path: str | Path = "data.json",
    seed: int = 42,
) -> Dict[str, Any]:
    random.seed(seed)

    vendors: List[Vendor] = []
    for i in range(1, num_vendors + 1):
        reliability = max(0.3, min(1.0, random.gauss(0.8, 0.15)))
        avg_delay = max(0, (1 - reliability) * random.uniform(3, 20))
        vendors.append(
            Vendor(
                vendor_id=f"V{i:03d}",
                vendor_name=f"Vendor {i}",
                reliability_score=round(reliability, 2),
                avg_delay_days=round(avg_delay, 1),
            )
        )

    projects: List[Project] = []
    risks: List[Risk] = []

    today = date.today()
    base_year = today.year
    project_start_base = date(base_year - 1, 1, 1)

    for i in range(1, num_projects + 1):
        project_id = f"P{i:03d}"
        project_name = f"Project {i:03d} - {random.choice(ASSET_TYPES)}"
        asset_type = random.choice(ASSET_TYPES)
        location = random.choice(LOCATIONS)

        budget = float(round(random.uniform(100_000, 10_000_000), 2))

        # Schedule
        planned_start = _rand_date(project_start_base, 365)
        planned_duration = random.randint(90, 360)
        planned_end = planned_start + timedelta(days=planned_duration)

        # Actual start may shift
        start_delay = random.choice([0, 0, 0, random.randint(1, 90)])
        actual_start = planned_start + timedelta(days=start_delay)

        # Vendor relationship influences delays
        vendor = random.choice(vendors)
        vendor_delay = int(max(0, random.gauss(vendor.avg_delay_days, 4)))

        # Some projects finish early / late
        duration_variation = int(random.gauss(0, 30)) + vendor_delay
        actual_end = planned_end + timedelta(days=duration_variation)

        # Cost profile
        cost_variation_factor = random.gauss(1.0, 0.15)
        # Force some over budget
        if random.random() < 0.3:
            cost_variation_factor += abs(random.gauss(0.25, 0.12))
        actual_cost = float(round(budget * cost_variation_factor, 2))

        # percent complete based on date
        if today < actual_start:
            percent_complete = 0.0
        elif today > actual_end:
            percent_complete = 1.0
        else:
            total_days = (actual_end - actual_start).days
            elapsed = (today - actual_start).days
            percent_complete = _clamp(elapsed / max(1, total_days), 0.0, 1.0)

        status = "Planned"
        if percent_complete >= 1.0:
            status = "Completed"
        elif percent_complete > 0.0:
            status = "Active"
        if actual_end > planned_end and percent_complete < 1.0:
            status = "Delayed"

        roi_expected = round(random.uniform(0.08, 0.25), 3)
        roi_actual = round(roi_expected + random.gauss(0, 0.05), 3)

        risk_score = _clamp(random.random() * 0.7 + (1 - vendor.reliability_score) * 0.4, 0.0, 1.0)

        projects.append(
            Project(
                project_id=project_id,
                project_name=project_name,
                asset_type=asset_type,
                location=location,
                vendor_id=vendor.vendor_id,
                budget_usd=budget,
                actual_cost_usd=actual_cost,
                planned_start_date=planned_start,
                planned_end_date=planned_end,
                actual_start_date=actual_start,
                actual_end_date=actual_end,
                percent_complete=round(percent_complete, 3),
                status=status,
                roi_expected=roi_expected,
                roi_actual=roi_actual,
                risk_score=round(risk_score, 3),
            )
        )

        # Add risk entries for about 30% of projects
        if random.random() < 0.3:
            num_risks = random.randint(1, 3)
            for r in range(num_risks):
                risk = Risk(
                    risk_id=f"R{len(risks)+1:04d}",
                    project_id=project_id,
                    risk_type=random.choice(RISK_TYPES),
                    probability=round(random.uniform(0.2, 0.95), 2),
                    impact_cost=round(random.uniform(0.05, 0.3) * budget, 2),
                    impact_days=random.randint(7, 90),
                )
                risks.append(risk)

    payload: Dict[str, Any] = {
        "projects": [p.model_dump() for p in projects],
        "risks": [r.model_dump() for r in risks],
        "vendors": [v.model_dump() for v in vendors],
    }

    output = Path(output_path)
    output.write_text(json.dumps(payload, indent=2, default=str))
    return payload


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate synthetic capex portfolio data.")
    parser.add_argument("--out", default="data.json", help="Output JSON file path")
    parser.add_argument("--projects", type=int, default=80, help="Number of projects to generate")
    parser.add_argument("--vendors", type=int, default=15, help="Number of vendors to generate")
    args = parser.parse_args()

    print("Generating synthetic dataset...")
    generate_synthetic_data(num_projects=args.projects, num_vendors=args.vendors, output_path=args.out)
    print(f"Data written to {args.out}")
