import json
from typing import Dict, Any
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL

# See: Structured Outputs & Responses API. The model will adhere to this JSON schema.
# Docs: Structured outputs & Responses API migration. 
# (We avoid brittle text parsing by constraining the output.) 
# :contentReference[oaicite:1]{index=1}

SCHEMA = {
    "name": "estimator_scaling_factors",
    "schema": {
        "type": "object",
        "properties": {
            "scaling_factors": {
                "type": "object",
                "properties": {
                    "capacity_scale_factor": {"type": "number"},
                    "regional_index_factor": {"type": "number"},
                    "inflation_factor": {"type": "number"},
                    "complexity_modifier": {"type": "number"}
                },
                "required": [
                    "capacity_scale_factor","regional_index_factor",
                    "inflation_factor","complexity_modifier"
                ],
                "additionalProperties": False
            },
            "soft_costs": {
                "type": "object",
                "properties": {
                    "engineering_pct": {"type": "number"},
                    "contingency_pct": {"type": "number"}
                },
                "required": ["engineering_pct","contingency_pct"],
                "additionalProperties": False
            },
            "reasoning": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1
            }
        },
        "required": ["scaling_factors","soft_costs","reasoning"],
        "additionalProperties": False
    }
}

SYSTEM_PROMPT = """You are the Estimator Agent for Capital Investment Projects.

You DO NOT calculate final costs.
Your job is to analyze similar historical projects and determine ADJUSTMENT FACTORS for:
- Capacity scaling (sub-linear for mechanical; modest for civil/electrical)
- Regional cost index (labor + materials productivity)
- Construction inflation (year differences)
- Complexity (layout constraints, shutdown integration, hygienic/GMP constraints)

Return ONLY scaling factors and assumptions in JSON. No currency values.

Rules:
- capacity_scale_factor: ratio-based with diminishing returns (e.g., 350->400 cpm ≈ +14% demand → factor ~1.10–1.15, not linear 1.14)
- regional_index_factor: NA baseline=1.00; Europe often 1.05–1.15 depending on labor intensity
- inflation_factor: 2%–6% per year typical; comp based on execution_years provided
- complexity_modifier:
  - Greenfield = 1.00
  - Brownfield simple tie-in = 1.03–1.08
  - Tight space, shutdown integration, GMP/cleanliness constraints = 1.10–1.25

Output MUST conform to the provided JSON schema.
"""

class EstimatorAgent:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def _format_projects(self, df):
        # minimal fields to reason about factors
        cols = ["project_id","project_type","region","capacity","execution_year"]
        # include WBS keys to hint at labor intensity
        cols += ["civil_cost","mechanical_cost","electrical_cost","automation_cost"]
        return df[cols].to_dict(orient="records")

    def infer_factors(self, similar_df, request: Dict[str, Any]) -> Dict[str, Any]:
        similar_projects = self._format_projects(similar_df)

        input_content = (
            "Given the following similar projects and a new project request, "
            "determine the appropriate adjustment factors.\n\n"
            f"Similar Projects:\n{json.dumps(similar_projects, indent=2)}\n\n"
            f"New Request:\n{json.dumps(request, indent=2)}\n\n"
            "Return ONLY JSON."
        )

        resp = self.client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": input_content}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": SCHEMA  # include name + schema
            }
        )

        # ✅ The returned JSON is in message.content, not .parsed
        raw_json = resp.choices[0].message.content

        # ✅ Ensure we parse it safely
        return json.loads(raw_json)

