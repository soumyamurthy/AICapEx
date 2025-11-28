import os

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# Regional cost/productivity indices (baseline NA=1.00)
REGIONAL_INDEX = {
    "North America": 1.00,
    "Europe": 1.08,   # typical 1.05–1.15 range, adjustable
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
