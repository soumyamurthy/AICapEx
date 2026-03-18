"""FastAPI backend for the AI Capex Project Copilot."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .ai import ask
from .data_gen import generate_synthetic_data
from .models import AskRequest, Project, Risk, Vendor
from .services import (
    build_portfolio_summary,
    format_project_for_api,
    load_data,
    predict_risks,
    calculate_cost_overrun_pct,
    calculate_schedule_variance,
)


load_dotenv()

DATA_PATH = os.getenv("DATA_PATH", "backend/data.json")

app = FastAPI(title="AI Capex Project Copilot API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _ensure_data() -> Dict[str, Any]:
    data_file = Path(DATA_PATH)
    if not data_file.exists():
        # Generate and write synthetic data
        generate_synthetic_data(output_path=str(data_file))
    return load_data(str(data_file))


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/projects")
def get_projects() -> List[Dict[str, Any]]:
    data = _ensure_data()
    projects: List[Project] = data["projects"]
    vendors: List[Vendor] = data["vendors"]
    return [format_project_for_api(p, vendors) for p in projects]


@app.get("/projects/{project_id}")
def get_project(project_id: str) -> Dict[str, Any]:
    data = _ensure_data()
    projects: List[Project] = data["projects"]
    vendors: List[Vendor] = data["vendors"]
    risks: List[Risk] = data["risks"]

    proj = next((p for p in projects if p.project_id == project_id), None)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    related_risks = [r for r in risks if r.project_id == project_id]
    proj_data = format_project_for_api(proj, vendors)
    proj_data["risks"] = [r.model_dump() for r in related_risks]
    proj_data["vendor"] = next((v.model_dump() for v in vendors if v.vendor_id == proj.vendor_id), None)
    proj_data["recommendations"] = []

    # Add recommended actions
    if proj_data.get("high_delay_risk"):
        proj_data["recommendations"].append(
            "Recommended action: Engage with vendor to validate lead times and add schedule buffer."
        )
    if proj_data.get("cost_overrun_risk"):
        proj_data["recommendations"].append(
            "Recommended action: Review scope and reduce non-critical items to control costs."
        )

    return proj_data


@app.get("/portfolio/summary")
def portfolio_summary() -> Dict[str, Any]:
    data = _ensure_data()
    projects: List[Project] = data["projects"]
    vendors: List[Vendor] = data["vendors"]
    risks: List[Risk] = data["risks"]

    summary = build_portfolio_summary(projects, risks, vendors)
    return summary


@app.get("/risks")
def get_risks() -> List[Dict[str, Any]]:
    data = _ensure_data()
    risks: List[Risk] = data["risks"]
    return [r.model_dump() for r in risks]


@app.post("/ask")
def ask_question(body: AskRequest) -> Dict[str, Any]:
    data = _ensure_data()
    projects: List[Project] = data["projects"]
    risks: List[Risk] = data["risks"]
    vendors: List[Vendor] = data["vendors"]

    response = ask(body.question, projects, risks, vendors)
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
