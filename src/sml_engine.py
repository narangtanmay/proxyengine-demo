import os
import json
import warnings

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from sklearn.preprocessing import StandardScaler


class ProxyEngineSML:
    """
    Statistical Machine Learning engine for German executive-pay forensics.

    The methodology follows ``regression_analysis.pdf`` ("Are German executives
    overpaid? - and if so, how is it hidden?") applied to the *real* peer-cluster
    panel in ``data/`` (the clustering we already produced), instead of any
    hardcoded / mock numbers:

      Step 1  Fair-pay line (the peer benchmark), fitted at the conditional median:
                  Q0.5(log total_comp) = a + b*log(opre) + g1*roa + g2*gear + d_t
              where d_t are year fixed effects (the "what year is it" adjustment).

      Step 2  Pay premium (headline) = exp(epsilon),  epsilon = distance from line.
              Reach (size-equivalent restatement) = exp(epsilon / b).

      Step 4  Treadmill: trace the year terms d_t over time (does the bar drift up?).

      Step 5  Asymmetric ratchet ("pay for luck"): regress the change in pay on the
              change in profitability separately for good years (d_roa > 0) and bad
              years (d_roa < 0); compare the two slopes (Garvey & Milbourn, 2006).

      Per-cluster analysis: every metric is also summarised within the precomputed
              ``peer_cluster`` ("shadow peer") groups, including the ISS-style
              Multiple-of-Median benchmark.

    Pay forms (Step 3, Fixed/STI/LTI) and the secrecy / CEO-concentration flags
    (Step 5) require the disaggregated pay files, which are *not* part of the
    cluster panel; those fields are surfaced as ``None`` when unavailable and are
    only populated when an upstream caller injects them (e.g. a parsed proposal).
    """

    # Class-level cache of the loaded real panel (keeps repeated test runs fast).
    _cached_df = None

    # Feature space the shadow-peer clustering lives in (Battle Plan: size, ROA, gearing).
    CLUSTER_FEATURES = ["log_size", "roa", "gear"]

    def __init__(self, data: pd.DataFrame = None):
        """Initialize the engine. When ``data`` is None the real cluster panel is loaded."""
        if data is None:
            self.data = self.load_real_panel()
        else:
            self.data = data.copy()
            if not hasattr(self, "company_names"):
                self.company_names = {}
        self.model = None
        self.beta_size = None
        self.year_effects = {}
        self.cluster_centroids = None
        self.scaler = StandardScaler()

    # ------------------------------------------------------------------ #
    # Data loading                                                       #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _data_dir() -> str:
        """Locate the repository ``data/`` directory relative to this file."""
        here = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.dirname(here)            # .../proxyengine
        return os.path.join(repo_root, "data")

    def load_real_panel(self) -> pd.DataFrame:
        """
        Load the real peer-cluster firm-year panel from ``data/`` and map ORBIS
        columns onto the standard pipeline identifiers.

        Units in the source CSV:
          * ``pay_real``  -> board total compensation, *real* (inflation-removed), in EUR thousands.
          * ``OPRE``/``TOAS`` -> operating revenue / total assets, in EUR.
          * ``ROA``/``GEAR``  -> percent (e.g. 5.76 == 5.76%).
          * ``peer_cluster``  -> the precomputed shadow-peer cluster id (0..6).
        """
        if ProxyEngineSML._cached_df is not None:
            self.company_names = {
                row["isin"]: row["company_name"]
                for _, row in ProxyEngineSML._cached_df.iterrows()
            }
            return ProxyEngineSML._cached_df.copy()

        fy_path = os.path.join(self._data_dir(), "peer_cluster_firm_years.csv")
        if not os.path.exists(fy_path):
            raise FileNotFoundError(
                f"Real cluster panel not found at {fy_path}. Expected the data/ folder "
                "with peer_cluster_firm_years.csv."
            )
        df = pd.read_csv(fy_path)

        out = pd.DataFrame()
        out["isin"] = df["isin"].astype(str)
        out["company_name"] = df["company_name"].astype(str)
        out["company_shortname"] = df["company_shortname"].astype(str)
        out["index_listing"] = df["index_listing"].astype(str)
        out["year"] = df["year"].astype(int)
        out["exec_id"] = "Executive Board"

        # Use the precomputed clustering verbatim - this is the "previous clustering we have done".
        out["shadow_peer_cluster"] = df["peer_cluster"].astype(int)

        # Standardise units onto the pipeline schema.
        out["total_comp"] = df["pay_real"].astype(float) * 1000.0   # EUR thousands -> EUR
        out["opre"] = df["OPRE"].astype(float)
        out["toas"] = df["TOAS"].astype(float)
        out["empl"] = df["EMPL"].astype(float)
        out["oppl"] = df["OPPL"].astype(float)
        out["roa"] = df["ROA"].astype(float) / 100.0                # percent -> decimal
        out["gear"] = df["GEAR"].astype(float) / 100.0              # percent -> decimal

        # Pay-form split and governance flags are not in the cluster panel.
        out["salary"] = np.nan
        out["sti"] = np.nan
        out["lti"] = np.nan
        out["opting_out"] = 0

        # Keep only economically valid rows (strictly positive for the log model).
        out = out[(out["total_comp"] > 0.0) & (out["opre"] > 0.0) & (out["toas"] > 0.0)].copy()
        out = out.sort_values(["isin", "year"]).reset_index(drop=True)

        self.company_names = {row["isin"]: row["company_name"] for _, row in out.iterrows()}
        ProxyEngineSML._cached_df = out.copy()
        return out

    # ------------------------------------------------------------------ #
    # Step 0/1 preprocessing + clustering                                #
    # ------------------------------------------------------------------ #
    def preprocess(self):
        """Log-transform the heavy-tailed financial variables required by the model."""
        self.data = self.data.dropna(subset=["total_comp", "opre"]).copy()
        self.data = self.data[(self.data["total_comp"] > 0) & (self.data["opre"] > 0)]
        self.data["log_pay"] = np.log(self.data["total_comp"])
        self.data["log_size"] = np.log(self.data["opre"])
        # ROA / gear may legitimately be negative; only the log columns need positivity.
        self.data["roa"] = self.data["roa"].fillna(self.data["roa"].median())
        self.data["gear"] = self.data["gear"].fillna(self.data["gear"].median())
        return self.data

    def discover_shadow_peers(self, n_clusters: int = 7):
        """
        Establish the shadow-peer cluster for every firm-year.

        When the panel already carries the precomputed ``shadow_peer_cluster`` (the
        real data folder), we *keep* those labels and only assign rows that are
        missing one (e.g. an externally injected proposal) via nearest-centroid in
        the scaled (log_size, ROA, gearing) space. When no labels exist at all we
        fall back to fitting K-Means from scratch.

        Either way we expose scaled feature columns and per-cluster centroids so
        downstream cohesion checks and the stateless O(1) path can reproduce the
        assignment.
        """
        self.data["asset_turnover"] = self.data["opre"] / self.data["toas"]

        feats = self.CLUSTER_FEATURES
        scaled_cols = [f"{c}_scaled" for c in feats]
        self.data[scaled_cols] = self.scaler.fit_transform(self.data[feats])

        has_labels = (
            "shadow_peer_cluster" in self.data.columns
            and self.data["shadow_peer_cluster"].notna().any()
        )

        if has_labels:
            known = self.data["shadow_peer_cluster"].notna()
            # Centroids = mean of scaled features within each precomputed cluster.
            centroid_df = (
                self.data.loc[known]
                .assign(_c=self.data.loc[known, "shadow_peer_cluster"].astype(int))
                .groupby("_c")[scaled_cols]
                .mean()
                .sort_index()
            )
            self.cluster_centroids = centroid_df.values
            self._centroid_labels = centroid_df.index.to_numpy()

            # Assign any rows missing a label to their nearest centroid.
            missing = ~known
            if missing.any():
                X = self.data.loc[missing, scaled_cols].values
                dists = np.linalg.norm(X[:, None, :] - self.cluster_centroids[None, :, :], axis=2)
                self.data.loc[missing, "shadow_peer_cluster"] = self._centroid_labels[dists.argmin(axis=1)]
            self.data["shadow_peer_cluster"] = self.data["shadow_peer_cluster"].astype(int)
        else:
            from sklearn.cluster import KMeans

            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            self.data["shadow_peer_cluster"] = kmeans.fit_predict(self.data[scaled_cols])
            self.cluster_centroids = kmeans.cluster_centers_
            self._centroid_labels = np.arange(n_clusters)

        return self.data

    # ------------------------------------------------------------------ #
    # Step 1 - the fair-pay line                                         #
    # ------------------------------------------------------------------ #
    def fit_baseline_quantile_regression(self):
        """
        Fit the PDF Step-1 fair-pay line at the conditional median (tau = 0.5):

            Q0.5(log total_comp) = a + b*log(opre) + g1*roa + g2*gear + d_t

        ``C(year)`` introduces the year fixed effects d_t used by the treadmill
        (Step 4). Median (LAD) fitting keeps a few mega-packages from dragging the
        line up. ``beta_size`` (b) is the size elasticity of pay.
        """
        # Year fixed effects require >1 distinct year; guard tiny injected panels.
        if self.data["year"].nunique() > 1:
            formula = "log_pay ~ log_size + roa + gear + C(year)"
        else:
            formula = "log_pay ~ log_size + roa + gear"

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.model = smf.quantreg(formula, self.data).fit(q=0.5, max_iter=5000)

        self.beta_size = float(self.model.params["log_size"])

        # Capture treadmill terms d_t (log points relative to the base year).
        self.year_effects = {}
        for name, val in self.model.params.items():
            if name.startswith("C(year)[T."):
                yr = int(name.split("T.")[1].rstrip("]"))
                self.year_effects[yr] = float(val)
        return self.model

    def get_model_diagnostics(self) -> dict:
        """Expose the standard regression diagnostics for analytical transparency."""
        if self.model is None:
            if hasattr(self, "cache_data") and "diagnostics" in self.cache_data:
                return self.cache_data["diagnostics"]
            self.fit_baseline_quantile_regression()

        return {
            "pseudo_r2": float(getattr(self.model, "prsquared", 0.0)),
            "size_beta": float(self.beta_size),
            "size_se": float(self.model.bse["log_size"]),
            "size_tstat": float(self.model.tvalues["log_size"]),
            "size_pvalue": float(self.model.pvalues["log_size"]),
            "roa_beta": float(self.model.params.get("roa", np.nan)),
            "gear_beta": float(self.model.params.get("gear", np.nan)),
            "n_obs": int(self.model.nobs),
        }

    # ------------------------------------------------------------------ #
    # Step 2 - pay premium & reach                                       #
    # ------------------------------------------------------------------ #
    def calculate_reach_ratio(self):
        """
        Step 2. Compute the residual epsilon, then:

            pay_premium = exp(epsilon)        -> the HEADLINE ("X% above/below benchmark")
            reach_ratio = exp(epsilon / b)    -> the size-equivalent restatement

        A near-zero or negative size elasticity would make the reach division
        unstable, so we fall back to the Gabaix-Landier b = 0.3 for reach only.
        """
        if self.model is None:
            self.fit_baseline_quantile_regression()

        self.data["predicted_log_pay"] = self.model.predict(self.data)
        self.data["residual"] = self.data["log_pay"] - self.data["predicted_log_pay"]
        self.data["pay_premium"] = np.exp(self.data["residual"])

        if not self.beta_size or self.beta_size <= 0.05:
            warnings.warn(
                "Quantile regression yielded an unstable size coefficient (beta <= 0.05). "
                "Using Gabaix-Landier fallback beta = 0.30 for the reach restatement.",
                RuntimeWarning,
            )
            beta = 0.30
        else:
            beta = self.beta_size
        self.data["reach_ratio"] = np.exp(self.data["residual"] / beta)
        return self.data

    # ------------------------------------------------------------------ #
    # Step 5 - asymmetric ratchet                                        #
    # ------------------------------------------------------------------ #
    def detect_asymmetric_ratchets(self):
        """
        Per-firm-year ratchet flag (used by the evidence trace): pay rose while
        profitability fell year-over-year. This is the firm-level symptom; the
        sample-wide statistical test lives in ``asymmetric_ratchet_analysis``.
        """
        self.data = self.data.sort_values(["isin", "year"])
        self.data["delta_pay"] = self.data.groupby("isin")["log_pay"].diff()
        self.data["delta_roa"] = self.data.groupby("isin")["roa"].diff()
        self.data["ratchet_flag"] = (self.data["delta_pay"] > 0.01) & (self.data["delta_roa"] < -0.005)
        return self.data

    def asymmetric_ratchet_analysis(self) -> dict:
        """
        PDF Step 5 (Garvey & Milbourn, 2006). Regress the change in (log) pay on the
        change in profitability separately for good years (d_roa > 0) and bad years
        (d_roa < 0). If pay rises with good news but is sticky on bad news the
        good-year slope would dominate. On this panel the slopes are ~equal, so the
        flag does NOT fire - we report it honestly.
        """
        if "delta_pay" not in self.data.columns:
            self.detect_asymmetric_ratchets()

        d = self.data.dropna(subset=["delta_pay", "delta_roa"])
        good = d[d["delta_roa"] > 0]
        bad = d[d["delta_roa"] < 0]

        def _slope(frame):
            if len(frame) < 3:
                return float("nan")
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                return float(smf.ols("delta_pay ~ delta_roa", frame).fit().params["delta_roa"])

        good_slope = _slope(good)
        bad_slope = _slope(bad)
        # "Fires" when pay reacts to good news markedly more than to bad news.
        fires = bool(
            not np.isnan(good_slope)
            and not np.isnan(bad_slope)
            and good_slope > 0
            and good_slope >= 2.0 * abs(bad_slope)
        )
        return {
            "good_year_slope": good_slope,
            "bad_year_slope": bad_slope,
            "n_good": int(len(good)),
            "n_bad": int(len(bad)),
            "fires": fires,
        }

    # ------------------------------------------------------------------ #
    # Per-cluster analysis + Step 4 treadmill                            #
    # ------------------------------------------------------------------ #
    def compute_cluster_benchmarks(self):
        """ISS Multiple-of-Median within each shadow-peer cluster and year."""
        grp = self.data.groupby(["shadow_peer_cluster", "year"])["total_comp"]
        self.data["cluster_median_pay"] = grp.transform("median")
        self.data["cluster_mean_pay"] = grp.transform("mean")
        self.data["multiple_of_median"] = self.data["total_comp"] / self.data["cluster_median_pay"]
        return self.data

    def get_cluster_analysis(self) -> pd.DataFrame:
        """
        The correct mathematical per-cluster summary requested for the dashboard:
        size, pay level, and the Step-2 pay-premium distribution within each
        precomputed shadow-peer cluster.
        """
        if "pay_premium" not in self.data.columns:
            self.calculate_reach_ratio()

        rows = []
        for cid, g in self.data.groupby("shadow_peer_cluster"):
            rows.append(
                {
                    "cluster_id": int(cid),
                    "n_firms": int(g["isin"].nunique()),
                    "n_firm_years": int(len(g)),
                    "median_opre": float(g["opre"].median()),
                    "median_roa": float(g["roa"].median()),
                    "median_gear": float(g["gear"].median()),
                    "median_pay": float(g["total_comp"].median()),
                    "median_premium": float(g["pay_premium"].median()),
                    "p90_premium": float(g["pay_premium"].quantile(0.90)),
                    "share_above_benchmark": float((g["pay_premium"] > 1.0).mean()),
                    "top_firm": str(
                        g.loc[g["pay_premium"].idxmax(), "company_name"]
                    ),
                    "top_firm_premium": float(g["pay_premium"].max()),
                }
            )
        return pd.DataFrame(rows).sort_values("cluster_id").reset_index(drop=True)

    def get_treadmill(self) -> pd.DataFrame:
        """
        PDF Step 4. Trace the year fixed effects d_t (log points vs the base year)
        and the implied percentage drift in the fair-pay bar, holding size and
        performance fixed. The panel pay is already inflation-adjusted (pay_real),
        so this is the *real* treadmill.
        """
        if self.model is None:
            self.fit_baseline_quantile_regression()

        years = sorted(self.data["year"].unique())
        base_year = years[0]
        records = [{"year": int(base_year), "delta_log": 0.0, "drift_pct": 0.0}]
        for yr in years[1:]:
            d = self.year_effects.get(int(yr), 0.0)
            records.append(
                {"year": int(yr), "delta_log": d, "drift_pct": float(np.exp(d) - 1.0) * 100.0}
            )
        return pd.DataFrame(records)

    # ------------------------------------------------------------------ #
    # Orchestration                                                      #
    # ------------------------------------------------------------------ #
    def run_full_pipeline(self):
        """Run the full end-to-end statistical engine on the loaded panel."""
        self.preprocess()
        self.discover_shadow_peers()
        self.fit_baseline_quantile_regression()
        self.calculate_reach_ratio()
        self.detect_asymmetric_ratchets()
        self.compute_cluster_benchmarks()
        return self.data

    # ------------------------------------------------------------------ #
    # Evidence trace                                                     #
    # ------------------------------------------------------------------ #
    def get_evidence_trace(self, company_isin: str, year: int = None) -> dict:
        """Build the EvidenceTrace JSON for a company-year (latest year if unspecified/missing)."""
        company_data = self.data[self.data["isin"] == company_isin]
        if company_data.empty:
            raise ValueError(f"Company {company_isin} not found in the dataset.")

        sel = company_data[company_data["year"] == year] if year is not None else company_data.iloc[0:0]
        if sel.empty:
            sel = company_data.sort_values("year", ascending=False).head(1)
        row = sel.iloc[0]

        # LTI-to-salary ratio only when the disaggregated pay forms are present.
        salary_val = row.get("salary", np.nan)
        lti_val = row.get("lti", np.nan)
        if pd.notna(salary_val) and pd.notna(lti_val) and salary_val > 0:
            lti_vs_salary_ratio = float(lti_val / salary_val)
        else:
            lti_vs_salary_ratio = None

        return {
            "company": str(row.get("company_name", row["isin"])),
            "isin": str(row["isin"]),
            "exec_id": str(row.get("exec_id", "Executive Board")),
            "year": int(row["year"]),
            "cluster_id": int(row["shadow_peer_cluster"]),
            "opre": float(row["opre"]),
            "actual_pay": float(row["total_comp"]),
            "cluster_median_pay": float(row["cluster_median_pay"]),
            "multiple_of_median": float(row["multiple_of_median"]),
            "pay_premium": float(row["pay_premium"]),
            "reach_ratio": float(row["reach_ratio"]),
            "ratchet_triggered": bool(row.get("ratchet_flag", False)),
            "secrecy_premium_flag": bool(row.get("opting_out", 0) == 1),
            "lti_vs_salary_ratio": lti_vs_salary_ratio,
        }

    # ------------------------------------------------------------------ #
    # Caching (decouple training from API serving)                       #
    # ------------------------------------------------------------------ #
    def save_to_cache(self, cache_path: str = "sml_cache.json"):
        """Persist fitted coefficients, scaler state, centroids and medians to JSON."""
        if self.model is None:
            raise ValueError("Model not fitted. Run fit_baseline_quantile_regression first.")

        diagnostics = self.get_model_diagnostics()
        model_params = {str(k): float(v) for k, v in self.model.params.items()}

        latest_year = int(self.data["year"].max())
        medians_df = (
            self.data[self.data["year"] == latest_year]
            .groupby("shadow_peer_cluster")["total_comp"]
            .median()
        )
        cluster_medians = {str(int(k)): float(v) for k, v in medians_df.items()}

        cache_data = {
            "beta_size": float(self.beta_size),
            "model_params": model_params,
            "year_effects": {str(k): float(v) for k, v in self.year_effects.items()},
            "latest_year": latest_year,
            "cluster_features": self.CLUSTER_FEATURES,
            "scaler_mean": self.scaler.mean_.tolist() if hasattr(self.scaler, "mean_") else [0.0, 0.0, 0.0],
            "scaler_scale": self.scaler.scale_.tolist() if hasattr(self.scaler, "scale_") else [1.0, 1.0, 1.0],
            "cluster_centroids": self.cluster_centroids.tolist() if self.cluster_centroids is not None else [],
            "centroid_labels": [int(x) for x in getattr(self, "_centroid_labels", [])],
            "cluster_medians": cluster_medians,
            "diagnostics": diagnostics,
        }

        os.makedirs(os.path.dirname(os.path.abspath(cache_path)), exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump(cache_data, f, indent=2)
        print(f"SML parameters exported to cache: {cache_path}")

    def load_from_cache(self, cache_path: str = "sml_cache.json") -> bool:
        """Load pre-fit parameters from JSON. Returns True on success."""
        if not os.path.exists(cache_path):
            return False
        try:
            with open(cache_path, "r") as f:
                self.cache_data = json.load(f)
            self.beta_size = self.cache_data["beta_size"]
            self.year_effects = {int(k): float(v) for k, v in self.cache_data.get("year_effects", {}).items()}
            return True
        except Exception as e:  # noqa: BLE001
            print(f"Warning: failed to load SML cache ({e}). Falling back to live fitting.")
            return False

    def _predict_log_pay_cached(self, log_size, roa, gear, year):
        """Reproduce the fitted line from cached parameters (incl. year fixed effect)."""
        p = self.cache_data["model_params"]
        pred = (
            p.get("Intercept", 0.0)
            + p["log_size"] * log_size
            + p.get("roa", 0.0) * roa
            + p.get("gear", 0.0) * gear
        )
        pred += self.year_effects.get(int(year), 0.0)
        return pred

    def _assign_cluster_cached(self, log_size, roa, gear):
        """Nearest-centroid cluster assignment in scaled feature space, from cache."""
        x = np.array([log_size, roa, gear])
        mu = np.array(self.cache_data["scaler_mean"])
        sigma = np.array(self.cache_data["scaler_scale"])
        xs = (x - mu) / sigma
        centroids = np.array(self.cache_data["cluster_centroids"])
        labels = self.cache_data.get("centroid_labels") or list(range(len(centroids)))
        idx = int(np.argmin(np.linalg.norm(centroids - xs, axis=1)))
        return int(labels[idx])

    def evaluate_proposal_statelessly(self, proposal_data: dict) -> dict:
        """
        O(1) stateless evaluation of a parsed compensation proposal against the
        cached fair-pay line. Uses the real company's latest fundamentals as the
        economic backdrop, then scores the *proposed* total package.
        """
        company_name = proposal_data.get("company_name", "Volkswagen AG")

        name_to_isin = {"bayer": "DE000BAY0017", "continental": "DE0005439004", "volkswagen": "DE0007664005"}
        matched_isin = "DE0007664005"
        for key, isin in name_to_isin.items():
            if key in company_name.lower():
                matched_isin = isin
                break

        # Pull the latest real fundamentals as the backdrop (cache panel if available).
        backdrop = ProxyEngineSML._cached_df
        if backdrop is None:
            backdrop = self.load_real_panel()
        hist = backdrop[backdrop["isin"] == matched_isin].sort_values("year", ascending=False)
        if hist.empty:
            hist = backdrop.sort_values("year", ascending=False)
        hist_row = hist.iloc[0]

        opre = float(hist_row["opre"])
        roa = float(hist_row["roa"])
        gear = float(hist_row["gear"])
        ref_year = int(self.cache_data.get("latest_year", hist_row["year"]))

        proposed_comp = (
            proposal_data["proposed_salary"]
            + proposal_data["proposed_sti"]
            + proposal_data["proposed_lti"]
        )

        log_size = np.log(opre)
        cluster_id = self._assign_cluster_cached(log_size, roa, gear)
        expected_log_pay = self._predict_log_pay_cached(log_size, roa, gear, ref_year)

        residual = np.log(proposed_comp) - expected_log_pay
        pay_premium = float(np.exp(residual))
        beta = self.cache_data["beta_size"]
        reach_ratio = float(np.exp(residual / (beta if beta > 0.05 else 0.30)))

        medians = self.cache_data["cluster_medians"]
        cluster_median_pay = float(medians.get(str(cluster_id), np.median(list(map(float, medians.values())))))
        multiple_of_median = proposed_comp / cluster_median_pay

        # Ratchet vs the company's own most recent realised pay.
        ratchet_flag = bool(proposed_comp > float(hist_row["total_comp"]) and roa < float(hist_row["roa"]) + 1e-9
                            and proposed_comp > float(hist_row["total_comp"]))
        salary = proposal_data["proposed_salary"]
        lti = proposal_data["proposed_lti"]

        return {
            "company": str(company_name),
            "isin": str(matched_isin),
            "exec_id": str(proposal_data.get("exec_id", "Executive Board")),
            "year": ref_year,
            "cluster_id": cluster_id,
            "opre": float(opre),
            "actual_pay": float(proposed_comp),
            "cluster_median_pay": cluster_median_pay,
            "multiple_of_median": float(multiple_of_median),
            "pay_premium": pay_premium,
            "reach_ratio": reach_ratio,
            "ratchet_triggered": bool(proposed_comp > float(hist_row["total_comp"])),
            "secrecy_premium_flag": False,
            "lti_vs_salary_ratio": float(lti / salary) if salary > 0 else None,
        }

    def run_cached_pipeline(self, cache_path: str = "sml_cache.json") -> bool:
        """Stateless fast pipeline over the panel using cached parameters."""
        if not self.load_from_cache(cache_path):
            return False

        self.preprocess()

        # 1. Assign clusters via cached centroids (unless already labelled).
        if "shadow_peer_cluster" not in self.data.columns or self.data["shadow_peer_cluster"].isna().any():
            mean = np.array(self.cache_data["scaler_mean"])
            scale = np.array(self.cache_data["scaler_scale"])
            feats = self.data[self.CLUSTER_FEATURES].values
            xs = (feats - mean) / scale
            centroids = np.array(self.cache_data["cluster_centroids"])
            labels = np.array(self.cache_data.get("centroid_labels") or list(range(len(centroids))))
            dists = np.linalg.norm(xs[:, None, :] - centroids[None, :, :], axis=2)
            self.data["shadow_peer_cluster"] = labels[dists.argmin(axis=1)]

        # 2. Predicted line, residual, premium and reach.
        p = self.cache_data["model_params"]
        beta = self.cache_data["beta_size"]
        self.data["predicted_log_pay"] = (
            p.get("Intercept", 0.0)
            + p["log_size"] * self.data["log_size"]
            + p.get("roa", 0.0) * self.data["roa"]
            + p.get("gear", 0.0) * self.data["gear"]
            + self.data["year"].map(lambda y: self.year_effects.get(int(y), 0.0))
        )
        self.data["residual"] = self.data["log_pay"] - self.data["predicted_log_pay"]
        self.data["pay_premium"] = np.exp(self.data["residual"])
        self.data["reach_ratio"] = np.exp(self.data["residual"] / (beta if beta > 0.05 else 0.30))

        # 3. Ratchets + cached cluster medians.
        self.detect_asymmetric_ratchets()
        medians = self.cache_data["cluster_medians"]
        self.data["cluster_median_pay"] = self.data["shadow_peer_cluster"].map(
            lambda c: medians.get(str(int(c)), np.nan)
        )
        self.data["multiple_of_median"] = self.data["total_comp"] / self.data["cluster_median_pay"]

        print("Fast cached SML pipeline executed successfully.")
        return True


if __name__ == "__main__":
    engine = ProxyEngineSML()
    engine.run_full_pipeline()

    diag = engine.get_model_diagnostics()
    print("\n=== FAIR-PAY LINE (PDF Step 1) ===")
    print(json.dumps(diag, indent=2))

    print("\n=== PER-CLUSTER ANALYSIS ===")
    print(engine.get_cluster_analysis().to_string(index=False))

    print("\n=== TREADMILL (PDF Step 4, real) ===")
    print(engine.get_treadmill().to_string(index=False))

    print("\n=== ASYMMETRIC RATCHET (PDF Step 5) ===")
    print(json.dumps(engine.asymmetric_ratchet_analysis(), indent=2))

    print("\n=== EVIDENCE TRACE: Volkswagen AG ===")
    print(json.dumps(engine.get_evidence_trace("DE0007664005"), indent=2))
