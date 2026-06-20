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
  actual_pay: number;
  cluster_median_pay: number;
  multiple_of_median: number;
  reach_ratio: number;
  ratchet_triggered: boolean;
  secrecy_premium_flag: boolean;
  lti_vs_salary_ratio: number;
}
