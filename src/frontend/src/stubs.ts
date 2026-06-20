import type { Company, DashboardData, ModelInfo } from "./types";

export const COMPANIES: Company[] = [
  { id: "DE0007664005", name: "Volkswagen AG" },
  { id: "DE000BAY0017", name: "Bayer AG" },
  { id: "DE0005439004", name: "Continental AG" },
];

// Offline fallbacks mirror the real SML engine output (latest available year, 2021)
// so the UI degrades gracefully to truthful numbers when the backend is unreachable.
export const FALLBACK_DASHBOARD_DATA: Record<string, DashboardData> = {
  "DE0007664005": {
    company: "Volkswagen AG",
    isin: "DE0007664005",
    exec_id: "Executive Board",
    year: 2021,
    cluster_id: 4,
    opre: 300914912689.0,
    actual_pay: 5906423.3,
    cluster_median_pay: 3334932.01,
    multiple_of_median: 1.77,
    pay_premium: 1.11,
    reach_ratio: 1.51,
    ratchet_triggered: false,
    secrecy_premium_flag: false,
    lti_vs_salary_ratio: null
  },
  "DE000BAY0017": {
    company: "Bayer AG",
    isin: "DE000BAY0017",
    exec_id: "Executive Board",
    year: 2021,
    cluster_id: 4,
    opre: 51625054615.0,
    actual_pay: 4323139.73,
    cluster_median_pay: 3334932.01,
    multiple_of_median: 1.30,
    pay_premium: 1.29,
    reach_ratio: 2.71,
    ratchet_triggered: false,
    secrecy_premium_flag: false,
    lti_vs_salary_ratio: null
  },
  "DE0005439004": {
    company: "Continental AG",
    isin: "DE0005439004",
    exec_id: "Executive Board",
    year: 2021,
    cluster_id: 0,
    opre: 45578667873.0,
    actual_pay: 3240373.03,
    cluster_median_pay: 2590914.79,
    multiple_of_median: 1.25,
    pay_premium: 0.96,
    reach_ratio: 0.85,
    ratchet_triggered: false,
    secrecy_premium_flag: false,
    lti_vs_salary_ratio: null
  }
};

// Fallback model-level diagnostics, matching the fitted PDF Step-1 fair-pay line on
// the real peer-cluster panel (n = 1163 firm-years, 2006-2021).
export const FALLBACK_MODEL_INFO: ModelInfo = {
  diagnostics: {
    pseudo_r2: 0.302,
    size_beta: 0.2518,
    size_se: 0.0088,
    size_tstat: 28.62,
    size_pvalue: 0.0,
    roa_beta: 0.7985,
    gear_beta: -0.0069,
    n_obs: 1163
  },
  ratchet: {
    good_year_slope: 0.4399,
    bad_year_slope: 0.3069,
    n_good: 517,
    n_bad: 514,
    fires: false
  },
  n_clusters: 7,
  year_min: 2006,
  year_max: 2021
};

export const PLACEHOLDER_ASSISTANT_REPLY =
  "The SML backend and Dual-Lens translator is initializing. If you see this, make sure the local FastAPI server is running on http://localhost:8000!";
