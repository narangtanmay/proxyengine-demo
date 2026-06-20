export type Role = "user" | "assistant";

export interface Message {
  id: string;
  role: Role;
  content: string;
  createdAt: number;
}

export interface Company {
  id: string;
  name: string;
}

export interface DashboardData {
  company: string;
  isin: string;
  exec_id: string;
  year: number;
  cluster_id: number;
  opre: number;
  actual_pay: number;
  cluster_median_pay: number;
  multiple_of_median: number;
  pay_premium: number;
  reach_ratio: number;
  ratchet_triggered: boolean;
  secrecy_premium_flag: boolean;
  lti_vs_salary_ratio: number | null;
  salary_benchmark?: number;
  sti_benchmark?: number;
  lti_benchmark?: number;
  _traceability_map?: Record<string, {
    origin: string;
    equation: string;
    file: string;
    line: number;
    description: string;
  }>;
}

export interface ModelInfo {
  diagnostics: {
    pseudo_r2: number;
    size_beta: number;
    size_se: number;
    size_tstat: number;
    size_pvalue: number;
    roa_beta: number;
    gear_beta: number;
    n_obs: number;
  };
  ratchet: {
    good_year_slope: number;
    bad_year_slope: number;
    n_good: number;
    n_bad: number;
    fires: boolean;
  };
  n_clusters: number;
  year_min: number;
  year_max: number;
}
