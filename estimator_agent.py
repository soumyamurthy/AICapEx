import json
from typing import Dict, Any, List
# from openai import OpenAI  # Demo: disabled for deterministic mode.
from config import REGIONAL_INDEX
# from config import OPENAI_API_KEY, OPENAI_MODEL  # Demo: disabled for deterministic mode.
from scaler import infer_inflation_factor

# See: Structured Outputs & Responses API. The model will adhere to this JSON schema.
# Docs: Structured outputs & Responses API migration. 
# (We avoid brittle text parsing by constraining the output.) 
# :contentReference[oaicite:1]{index=1}

SCHEMA_NAME = "estimator_scaling_factors"
ESTIMATE_SCHEMA = {
    "type": "object",
    "properties": {
        "scaling_factors": {
            "type": "object",
            "properties": {
                "capacity_scale_factor": {"type": "number", "minimum": 0.7, "maximum": 1.7},
                "regional_index_factor": {"type": "number", "minimum": 0.8, "maximum": 1.3},
                "inflation_factor": {"type": "number", "minimum": 0.75, "maximum": 1.4},
                "complexity_modifier": {"type": "number", "minimum": 0.95, "maximum": 1.25},
            },
            "required": [
                "capacity_scale_factor",
                "regional_index_factor",
                "inflation_factor",
                "complexity_modifier",
            ],
            "additionalProperties": False,
        },
        "soft_costs": {
            "type": "object",
            "properties": {
                "engineering_pct": {"type": "number", "minimum": 0.02, "maximum": 0.2},
                "contingency_pct": {"type": "number", "minimum": 0.02, "maximum": 0.25},
            },
            "required": ["engineering_pct", "contingency_pct"],
            "additionalProperties": False,
        },
        "reasoning": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 8,
        },
    },
    "required": ["scaling_factors", "soft_costs", "reasoning"],
    "additionalProperties": False,
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

Use available tools when useful:
- get_regional_index(region)
- inflation_between_years(base_execution_year, target_execution_year)

Output MUST conform to the provided JSON schema.
"""

TOOLS = [
    {
        "type": "function",
        "name": "get_regional_index",
        "description": "Lookup known regional index for labor/material productivity.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "region": {"type": "string"}
            },
            "required": ["region"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "inflation_between_years",
        "description": "Compute inflation factor from base year to target year.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "base_execution_year": {"type": "integer"},
                "target_execution_year": {"type": "integer"},
            },
            "required": ["base_execution_year", "target_execution_year"],
            "additionalProperties": False,
        },
    },
]

class EstimatorAgent:
    def __init__(self):
        # Demo mode: keep estimator deterministic by disabling OpenAI client.
        # self.client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
        self.client = None

    def _format_projects(self, df):
        # minimal fields to reason about factors
        cols = ["project_id","project_type","region","country","capacity","execution_year"]
        # include WBS keys to hint at labor intensity
        cols += ["civil_cost","mechanical_cost","electrical_cost","automation_cost"]
        for c in cols:
            if c not in df.columns:
                df[c] = "Unknown" if c in {"region", "country", "project_type"} else 0
        return df[cols].to_dict(orient="records")

    @staticmethod
    def _clamp(x: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, float(x)))

    def _tool_get_regional_index(self, region: str) -> Dict[str, Any]:
        return {"region": region, "regional_index": float(REGIONAL_INDEX.get(region, 1.0))}

    def _tool_inflation_between_years(self, base_execution_year: int, target_execution_year: int) -> Dict[str, Any]:
        base_factor = infer_inflation_factor(int(base_execution_year))
        target_factor = infer_inflation_factor(int(target_execution_year))
        ratio = base_factor / target_factor if target_factor else 1.0
        return {"factor": float(self._clamp(ratio, 0.75, 1.4))}

    def _fallback_estimate(self, similar_df, request: Dict[str, Any], reason: str) -> Dict[str, Any]:
        base_row = similar_df.iloc[0].to_dict()
        base_capacity = max(1.0, float(base_row.get("capacity", request["capacity"])))
        req_capacity = max(1.0, float(request["capacity"]))
        capacity_factor = self._clamp((req_capacity / base_capacity) ** 0.6, 0.7, 1.7)

        base_year = int(base_row.get("execution_year", request["execution_year"]))
        inflation = self._tool_inflation_between_years(base_year, int(request["execution_year"]))["factor"]
        region = self._tool_get_regional_index(request["region"])["regional_index"]

        contingency_hist = similar_df["contingency_pct"].dropna().astype(float)
        contingency_pct = float(contingency_hist.median()) if len(contingency_hist) else 0.1
        contingency_pct = self._clamp(contingency_pct, 0.02, 0.25)

        return {
            "scaling_factors": {
                "capacity_scale_factor": round(capacity_factor, 4),
                "regional_index_factor": round(float(region), 4),
                "inflation_factor": round(float(inflation), 4),
                "complexity_modifier": 1.05,
            },
            "soft_costs": {
                "engineering_pct": 0.08,
                "contingency_pct": round(contingency_pct, 4),
            },
            "reasoning": [
                "Fallback estimator used deterministic heuristics.",
                f"Capacity factor uses a sub-linear exponent from base capacity {base_capacity:.0f} to requested {req_capacity:.0f}.",
                f"Inflation was derived from year adjustment using base {base_year} to target {int(request['execution_year'])}.",
                reason,
            ],
            "meta": {"mode": "fallback"},
        }

    def _execute_tool_call(self, name: str, arguments_json: str) -> Dict[str, Any]:
        args = json.loads(arguments_json or "{}")
        if name == "get_regional_index":
            return self._tool_get_regional_index(region=str(args["region"]))
        if name == "inflation_between_years":
            return self._tool_inflation_between_years(
                base_execution_year=int(args["base_execution_year"]),
                target_execution_year=int(args["target_execution_year"]),
            )
        return {"error": f"Unknown tool: {name}"}

    def _responses_infer(self, input_content: str) -> Dict[str, Any]:
        response = self.client.responses.create(
            model=OPENAI_MODEL,
            instructions=SYSTEM_PROMPT,
            input=input_content,
            tools=TOOLS,
            tool_choice="auto",
            parallel_tool_calls=False,
            text={
                "format": {
                    "type": "json_schema",
                    "name": SCHEMA_NAME,
                    "schema": ESTIMATE_SCHEMA,
                    "strict": True,
                }
            },
        )

        for _ in range(4):
            tool_calls = [item for item in response.output if getattr(item, "type", "") == "function_call"]
            if not tool_calls:
                break

            tool_outputs: List[Dict[str, str]] = []
            for tc in tool_calls:
                tool_result = self._execute_tool_call(tc.name, tc.arguments)
                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": tc.call_id,
                        "output": json.dumps(tool_result),
                    }
                )

            response = self.client.responses.create(
                model=OPENAI_MODEL,
                previous_response_id=response.id,
                input=tool_outputs,
                tools=TOOLS,
                tool_choice="auto",
                parallel_tool_calls=False,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": SCHEMA_NAME,
                        "schema": ESTIMATE_SCHEMA,
                        "strict": True,
                    }
                },
            )

        return json.loads(response.output_text)

    def infer_factors(self, similar_df, request: Dict[str, Any]) -> Dict[str, Any]:
        if similar_df is None or similar_df.empty:
            raise ValueError("No similar projects available for estimation.")

        if self.client is None:
            return self._fallback_estimate(
                similar_df,
                request,
                "OPENAI_API_KEY is not set; AI reasoning was skipped.",
            )

        similar_projects = self._format_projects(similar_df)
        input_content = (
            "Given similar historical projects and a new project request, "
            "determine adjustment factors.\n\n"
            f"Similar Projects:\n{json.dumps(similar_projects, indent=2)}\n\n"
            f"New Request:\n{json.dumps(request, indent=2)}\n\n"
            "Return ONLY schema-compliant JSON."
        )

        try:
            out = self._responses_infer(input_content)
            out["meta"] = {"mode": "ai"}
            return out
        except Exception as exc:
            return self._fallback_estimate(similar_df, request, f"AI call failed: {str(exc)}")
