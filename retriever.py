import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler


class Retriever:
    """
    Comparable-project retriever:
    - filters by project_type
    - prioritizes country/region based on strictness settings
    - computes similarity over [capacity, region_index, execution_year]
    - can bias results toward newer projects via recency weighting
    """

    def __init__(self, csv_path: str, regional_index: dict):
        self.df = pd.read_csv(csv_path)
        self.df = self.df.dropna(subset=["project_type", "region", "capacity", "execution_year"])
        if "country" not in self.df.columns:
            self.df["country"] = "Unknown"
        self.df["country"] = self.df["country"].fillna("Unknown")
        self.regional_index = regional_index

        self.feature_df = self.df.copy()
        self.feature_df["region_idx"] = self.feature_df["region"].map(self.regional_index).fillna(1.0)
        self.X_all = self.feature_df[["capacity", "region_idx", "execution_year"]].to_numpy(dtype=float)
        self.scaler = MinMaxScaler().fit(self.X_all)

    def find_similar(
        self,
        request: dict,
        top_k: int = 5,
        strict_country: bool = False,
        recency_weight: float = 0.0,
        return_meta: bool = False,
    ):
        # constrain to same project_type first (most important)
        same_type = self.feature_df[self.feature_df["project_type"] == request["project_type"]]
        same_region = same_type[same_type["region"] == request["region"]] if not same_type.empty else same_type
        req_country = request.get("country")
        same_country = (
            same_region[same_region["country"] == req_country]
            if (not same_region.empty and req_country is not None)
            else same_region
        )

        if strict_country and len(same_country) > 0:
            candidate_df = same_country
            candidate_scope = "country_strict"
        elif len(same_country) >= top_k:
            candidate_df = same_country
            candidate_scope = "country"
        elif len(same_region) >= max(2, top_k // 2):
            candidate_df = same_region
            candidate_scope = "region"
        elif not same_type.empty:
            candidate_df = same_type
            candidate_scope = "type"
        else:
            # fall back to whole dataset if no same-type
            candidate_df = self.feature_df
            candidate_scope = "global"

        X = candidate_df[["capacity", "region_idx", "execution_year"]].to_numpy(dtype=float)
        X_scaled = self.scaler.transform(X)

        req_region_idx = self.regional_index.get(request["region"], 1.0)
        req_vector = np.array([[request["capacity"], req_region_idx, request["execution_year"]]], dtype=float)
        req_scaled = self.scaler.transform(req_vector)[0]

        recency_weight = float(max(0.0, min(1.0, recency_weight)))
        geom_dist = np.linalg.norm(X_scaled - req_scaled, axis=1)

        year_span = max(1.0, float(self.feature_df["execution_year"].max() - self.feature_df["execution_year"].min()))
        recency_penalty = (
            float(self.feature_df["execution_year"].max()) - candidate_df["execution_year"].astype(float).to_numpy()
        ) / year_span

        blended_dist = (1.0 - recency_weight) * geom_dist + recency_weight * recency_penalty

        sel_n = min(int(top_k), len(candidate_df))
        order = np.argsort(blended_dist)[:sel_n]
        sel = candidate_df.iloc[order].copy()

        sel_dist = blended_dist[order]
        similarity = 1.0 / (1.0 + sel_dist)
        sel["match_score"] = np.round(similarity * 100.0, 1)
        sel["distance_score"] = np.round(sel_dist, 4)

        comparable_quality = float(np.clip(np.mean(similarity), 0.0, 1.0)) if len(similarity) else 0.0

        cols_keep = [
            "project_id",
            "project_name",
            "project_type",
            "region",
            "country",
            "site",
            "capacity",
            "total_cost_usd",
            "civil_cost",
            "mechanical_cost",
            "electrical_cost",
            "automation_cost",
            "match_score",
            "distance_score",
            "contingency_pct",
            "execution_year",
        ]
        out = sel[cols_keep].reset_index(drop=True)
        if not return_meta:
            return out

        return out, {
            "candidate_scope": candidate_scope,
            "candidate_count": int(len(candidate_df)),
            "comparable_quality": round(comparable_quality * 100.0, 1),
        }
