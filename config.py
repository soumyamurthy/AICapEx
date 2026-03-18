import os
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


def _load_local_streamlit_secrets() -> dict:
    if tomllib is None:
        return {}
    secrets_path = Path(".streamlit/secrets.toml")
    if not secrets_path.exists():
        return {}
    try:
        with secrets_path.open("rb") as f:
            data = tomllib.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


_LOCAL_SECRETS = _load_local_streamlit_secrets()

OPENAI_MODEL = os.getenv("OPENAI_MODEL") or _LOCAL_SECRETS.get("OPENAI_MODEL", "gpt-5")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or _LOCAL_SECRETS.get("OPENAI_API_KEY")


# Regional cost/productivity indices (baseline NA=1.00)
REGIONAL_INDEX = {
    "North America": 1.00,
    "Europe": 1.08,   # typical 1.05–1.15 range, adjustable
    "Asia Pacific": 0.95,
    "Latin America": 0.88,
    "Middle East & Africa": 0.92,
}

REGION_COUNTRIES = {
    "North America": ["United States", "Canada", "Mexico"],
    "Europe": ["United Kingdom", "Germany", "France", "Italy", "Poland"],
    "Asia Pacific": ["China", "Japan", "India", "Singapore", "Australia", "Thailand"],
    "Latin America": ["Brazil", "Mexico", "Colombia", "Peru", "Chile"],
    "Middle East & Africa": ["United Arab Emirates", "Saudi Arabia", "South Africa", "Egypt", "Kenya"],
}

# Inflation table (simple illustrative; Y/Y cumulative factor to “today”)
# You can replace with a better series or pull from your corporate index later.
INFLATION_BY_YEAR = {
    2015: 1.28, 2016: 1.25, 2017: 1.22, 2018: 1.18, 2019: 1.15,
    2020: 1.12, 2021: 1.10, 2022: 1.07, 2023: 1.04
    # if execution_year not listed, default = 1.03 per year delta in scaler.py
}

# Complexity presets used by Reviewer to sanity check
COMPLEXITY_MIN_MAX = (0.95, 1.25)
