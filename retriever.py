import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.neighbors import NearestNeighbors

class Retriever:
    """
    Simple comparable-project retriever:
    - filters by project_type
    - encodes region as numeric (via config indices)
    - KNN over [capacity, region_index, execution_year]
    """

    def __init__(self, csv_path: str, regional_index: dict):
        self.df = pd.read_csv(csv_path)
        self.df = self.df.dropna(subset=["project_type","region","capacity","execution_year"])
        self.regional_index = regional_index

        self.feature_df = self.df.copy()
        self.feature_df["region_idx"] = self.feature_df["region"].map(self.regional_index).fillna(1.0)
        self.X_all = self.feature_df[["capacity", "region_idx", "execution_year"]].to_numpy(dtype=float)
        self.scaler = MinMaxScaler().fit(self.X_all)

    def find_similar(self, request: dict, top_k: int = 5):
        # constrain to same project_type first (most important)
        same_type = self.feature_df[self.feature_df["project_type"] == request["project_type"]]
        if same_type.empty:
            # fall back to whole dataset if no same-type
            candidate_df = self.feature_df
        else:
            candidate_df = same_type

        X = candidate_df[["capacity", "region_idx", "execution_year"]].to_numpy(dtype=float)
        X_scaled = self.scaler.transform(X)

        req_region_idx = self.regional_index.get(request["region"], 1.0)
        req_vector = np.array([[request["capacity"], req_region_idx, request["execution_year"]]], dtype=float)
        req_scaled = self.scaler.transform(req_vector)

        # KNN
        n_neighbors = min(top_k, len(candidate_df))
        nn = NearestNeighbors(n_neighbors=n_neighbors, metric="euclidean")
        nn.fit(X_scaled)
        dists, idxs = nn.kneighbors(req_scaled)

        sel = candidate_df.iloc[idxs[0]].copy()
        # All needed columns are already present, just return selection
        cols_keep = [
            "project_id","project_name","project_type","region","site","capacity",
            "total_cost_usd","civil_cost","mechanical_cost","electrical_cost","automation_cost",
            "contingency_pct","execution_year"
        ]
        return sel[cols_keep].reset_index(drop=True)

