from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field, PositiveFloat, constr


class Project(BaseModel):
    project_id: str
    project_name: str
    asset_type: str
    location: str
    vendor_id: str
    budget_usd: float
    actual_cost_usd: float
    planned_start_date: date
    planned_end_date: date
    actual_start_date: Optional[date]
    actual_end_date: Optional[date]
    percent_complete: float = Field(ge=0.0, le=1.0)
    status: Literal["Planned", "Active", "Delayed", "Completed"]
    roi_expected: float
    roi_actual: float
    risk_score: float = Field(ge=0.0, le=1.0)


class Risk(BaseModel):
    risk_id: str
    project_id: str
    risk_type: str
    probability: float = Field(ge=0.0, le=1.0)
    impact_cost: float
    impact_days: int


class Vendor(BaseModel):
    vendor_id: str
    vendor_name: str
    reliability_score: float = Field(ge=0.0, le=1.0)
    avg_delay_days: float


class AskRequest(BaseModel):
    question: constr(min_length=1)


class AskResponse(BaseModel):
    answer: str
    insights: list[str]
