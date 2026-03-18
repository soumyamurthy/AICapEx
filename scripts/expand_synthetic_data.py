import argparse
from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd

REGIONAL_INDEX = {
    "North America": 1.00,
    "Europe": 1.08,
    "Asia Pacific": 0.95,
    "Latin America": 0.88,
    "Middle East & Africa": 0.92,
}

EXPANDED_PROJECT_TYPES = [
    "Filling Line",
    "Packaging Line",
    "Processing System",
    "Plant Expansion",
    "Mixing & Blending",
    "Utilities Upgrade",
    "Warehouse Automation",
    "Quality Lab Upgrade",
]

REGION_TO_SITES = {
    "North America": ["Ontario Plant", "Ohio Plant", "Iowa Plant"],
    "Europe": ["Le Havre Plant", "Manchester Plant", "Modena Plant", "Warsaw Plant"],
    "Asia Pacific": ["Singapore Plant", "Bangkok Plant", "Guangzhou Plant", "Sydney Plant"],
    "Latin America": ["Sao Paulo Plant", "Monterrey Plant", "Lima Plant", "Bogota Plant"],
    "Middle East & Africa": ["Dubai Plant", "Johannesburg Plant", "Cairo Plant", "Riyadh Plant"],
}

REGION_TO_COUNTRIES = {
    "North America": ["United States", "Canada", "Mexico"],
    "Europe": ["United Kingdom", "Germany", "France", "Italy", "Poland"],
    "Asia Pacific": ["China", "Japan", "India", "Singapore", "Australia", "Thailand"],
    "Latin America": ["Brazil", "Mexico", "Colombia", "Peru", "Chile"],
    "Middle East & Africa": ["United Arab Emirates", "Saudi Arabia", "South Africa", "Egypt", "Kenya"],
}

TYPE_COST_MULTIPLIER = {
    "Filling Line": 1.00,
    "Packaging Line": 0.95,
    "Processing System": 1.10,
    "Plant Expansion": 1.20,
    "Mixing & Blending": 1.15,
    "Utilities Upgrade": 0.85,
    "Warehouse Automation": 0.90,
    "Quality Lab Upgrade": 0.70,
}


@dataclass
class GenConfig:
    input_csv: str
    output_csv: str
    end_year: int
    rows_per_year: int
    seed: int
    ensure_catalog_rows: int


def parse_args() -> GenConfig:
    parser = argparse.ArgumentParser(description="Expand synthetic CapEx dataset by generating future-year records.")
    parser.add_argument("--input", default="data/synthetic_capex_projects_optionA.csv")
    parser.add_argument("--output", default="data/synthetic_capex_projects_optionA.csv")
    parser.add_argument("--end-year", type=int, default=2028)
    parser.add_argument("--rows-per-year", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--ensure-catalog-rows",
        type=int,
        default=4,
        help="Minimum rows to ensure for each (region, project_type) combination in generated years.",
    )
    args = parser.parse_args()
    return GenConfig(
        input_csv=args.input,
        output_csv=args.output,
        end_year=args.end_year,
        rows_per_year=args.rows_per_year,
        seed=args.seed,
        ensure_catalog_rows=args.ensure_catalog_rows,
    )


def _next_serial(df: pd.DataFrame) -> int:
    serials = pd.to_numeric(df["project_id"].str.split("-").str[-1], errors="coerce").dropna()
    return int(serials.max()) + 1 if not serials.empty else 0


def _safe_ratio(a: float, b: float) -> float:
    return float(a / b) if b else 1.0


def _bounded(x: float, low: float, high: float) -> float:
    return float(max(low, min(high, x)))


def _sample_template(pool: pd.DataFrame, rng: np.random.Generator) -> pd.Series:
    idx = int(rng.integers(0, len(pool)))
    return pool.iloc[idx]


def _capacity_from_template(base_capacity: float, rng: np.random.Generator) -> int:
    cap = float(base_capacity) * float(np.exp(rng.normal(0.0, 0.16)))
    cap = _bounded(cap, 100, 2000)
    return int(round(cap))


def _cost_split(base: pd.Series) -> Dict[str, float]:
    keys = ["civil_cost", "mechanical_cost", "electrical_cost", "automation_cost"]
    total = float(sum(float(base[k]) for k in keys))
    if total <= 0:
        return {k: 0.25 for k in keys}
    return {k: float(base[k]) / total for k in keys}


def _make_row(template: pd.Series, year: int, serial: int, rng: np.random.Generator) -> dict:
    project_type = str(template["project_type"])
    region = str(template["region"])
    site = str(template["site"])
    country = str(template.get("country", rng.choice(REGION_TO_COUNTRIES.get(region, ["United States"]))))

    # Broaden type and geography coverage for future catalog.
    if float(rng.random()) < 0.45:
        project_type = str(rng.choice(EXPANDED_PROJECT_TYPES))
    if float(rng.random()) < 0.40:
        region = str(rng.choice(list(REGIONAL_INDEX.keys())))
        site = str(rng.choice(REGION_TO_SITES[region]))
        country = str(rng.choice(REGION_TO_COUNTRIES[region]))

    base_capacity = float(template["capacity"])
    new_capacity = _capacity_from_template(base_capacity, rng)

    # Nominal escalation and scaling heuristics.
    year_delta = int(year) - int(template["execution_year"])
    year_factor = 1.04 ** year_delta
    capacity_factor = _bounded((new_capacity / max(base_capacity, 1.0)) ** 0.62, 0.7, 1.7)

    # Keep region mostly stable with occasional drift between NA/Europe.
    if float(rng.random()) < 0.08:
        region = str(rng.choice(list(REGIONAL_INDEX.keys())))
        site = str(rng.choice(REGION_TO_SITES[region]))
        country = str(rng.choice(REGION_TO_COUNTRIES[region]))
    region_factor = _safe_ratio(REGIONAL_INDEX.get(region, 1.0), REGIONAL_INDEX.get(str(template["region"]), 1.0))
    type_factor = TYPE_COST_MULTIPLIER.get(project_type, 1.0) / TYPE_COST_MULTIPLIER.get(str(template["project_type"]), 1.0)

    complexity_noise = float(np.exp(rng.normal(0.0, 0.10)))
    total_multiplier = _bounded(year_factor * capacity_factor * region_factor * type_factor * complexity_noise, 0.55, 2.5)

    base_wbs_sum = float(template["civil_cost"] + template["mechanical_cost"] + template["electrical_cost"] + template["automation_cost"])
    target_wbs_sum = max(1_000_000.0, base_wbs_sum * total_multiplier)

    split = _cost_split(template)
    # Minor category jitter while preserving sum.
    jitter = {k: max(0.05, split[k] * float(np.exp(rng.normal(0.0, 0.08)))) for k in split}
    jitter_sum = sum(jitter.values())
    shares = {k: v / jitter_sum for k, v in jitter.items()}

    civil = round(target_wbs_sum * shares["civil_cost"], 2)
    mech = round(target_wbs_sum * shares["mechanical_cost"], 2)
    elec = round(target_wbs_sum * shares["electrical_cost"], 2)
    auto = round(target_wbs_sum * shares["automation_cost"], 2)

    contingency_pct = _bounded(float(template.get("contingency_pct", 0.11)) + float(rng.normal(0.0, 0.015)), 0.05, 0.20)
    engineering_pct = _bounded(0.08 + float(rng.normal(0.0, 0.015)), 0.05, 0.14)

    total_cost = round((civil + mech + elec + auto) * (1.0 + engineering_pct + contingency_pct), 2)

    name = f"{project_type} Project {serial:03d}"
    return {
        "project_id": f"P-{year}-{serial:03d}",
        "project_name": name,
        "project_type": project_type,
        "region": region,
        "country": country,
        "site": site,
        "capacity": int(new_capacity),
        "total_cost_usd": total_cost,
        "civil_cost": civil,
        "mechanical_cost": mech,
        "electrical_cost": elec,
        "automation_cost": auto,
        "contingency_pct": round(contingency_pct, 3),
        "execution_year": int(year),
    }


def _ensure_catalog_coverage(
    generated_rows: list,
    template_pool: pd.DataFrame,
    years: list,
    serial_start: int,
    min_rows_per_combo: int,
    rng: np.random.Generator,
) -> list:
    rows = list(generated_rows)
    serial = serial_start
    generated_df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["region", "project_type"])
    combos = [(region, ptype) for region in REGIONAL_INDEX for ptype in EXPANDED_PROJECT_TYPES]

    for region, ptype in combos:
        count = 0
        if not generated_df.empty:
            count = int(((generated_df["region"] == region) & (generated_df["project_type"] == ptype)).sum())
        needed = max(0, min_rows_per_combo - count)

        for _ in range(needed):
            template = _sample_template(template_pool, rng)
            year = int(rng.choice(years))
            row = _make_row(template, year=year, serial=serial, rng=rng)
            row["region"] = region
            row["project_type"] = ptype
            row["site"] = str(rng.choice(REGION_TO_SITES[region]))
            row["country"] = str(rng.choice(REGION_TO_COUNTRIES[region]))
            rows.append(row)
            serial += 1

    return rows


def main() -> None:
    cfg = parse_args()
    rng = np.random.default_rng(cfg.seed)

    df = pd.read_csv(cfg.input_csv)
    if "country" not in df.columns:
        df["country"] = df["region"].apply(lambda r: str(rng.choice(REGION_TO_COUNTRIES.get(str(r), ["United States"]))))
    else:
        missing_country = df["country"].isna() | (df["country"].astype(str).str.strip() == "")
        if missing_country.any():
            df.loc[missing_country, "country"] = df.loc[missing_country, "region"].apply(
                lambda r: str(rng.choice(REGION_TO_COUNTRIES.get(str(r), ["United States"])))
            )

    max_year = int(df["execution_year"].max())
    if cfg.end_year <= max_year:
        df.to_csv(cfg.output_csv, index=False)
        print("Backfilled country column where needed.")
        print(f"No generation needed. Dataset already reaches {max_year}.")
        return

    new_rows = []
    serial = _next_serial(df)

    # Bias templates to recent years for realistic near-future drift.
    recent = df[df["execution_year"] >= max_year - 2]
    template_pool = recent if len(recent) >= 20 else df

    generated_years = list(range(max_year + 1, cfg.end_year + 1))
    for year in generated_years:
        for _ in range(cfg.rows_per_year):
            template = _sample_template(template_pool, rng)
            row = _make_row(template, year=year, serial=serial, rng=rng)
            new_rows.append(row)
            serial += 1

    if generated_years and cfg.ensure_catalog_rows > 0:
        new_rows = _ensure_catalog_coverage(
            generated_rows=new_rows,
            template_pool=template_pool,
            years=generated_years,
            serial_start=serial,
            min_rows_per_combo=cfg.ensure_catalog_rows,
            rng=rng,
        )

    out = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
    out.to_csv(cfg.output_csv, index=False)

    print(f"Input rows: {len(df)}")
    print(f"Added rows: {len(new_rows)}")
    print(f"Output rows: {len(out)}")
    print(f"Year range: {int(out['execution_year'].min())}..{int(out['execution_year'].max())}")


if __name__ == "__main__":
    main()
