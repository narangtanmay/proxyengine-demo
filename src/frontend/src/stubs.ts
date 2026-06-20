import type { Company, DashboardData } from "./types";

export const COMPANIES: Company[] = [
  { id: "DE0007664039", name: "Volkswagen AG" },
  { id: "DE000BAY0017", name: "Bayer AG" },
  { id: "DE0005439004", name: "Continental AG" },
];

export const FALLBACK_DASHBOARD_DATA: Record<string, DashboardData> = {
  "DE0007664039": {
    company: "Volkswagen AG",
    isin: "DE0007664039",
    exec_id: "Oliver Blume",
    year: 2024,
    cluster_id: 3,
    actual_pay: 8000000.0,
    cluster_median_pay: 1585212.93,
    multiple_of_median: 5.05,
    reach_ratio: 11.7,
    ratchet_triggered: true,
    secrecy_premium_flag: false,
    lti_vs_salary_ratio: 3.0
  },
  "DE000BAY0017": {
    company: "Bayer AG",
    isin: "DE000BAY0017",
    exec_id: "Bill Anderson",
    year: 2024,
    cluster_id: 1,
    actual_pay: 5000000.0,
    cluster_median_pay: 3500000.0,
    multiple_of_median: 1.43,
    reach_ratio: 1.8,
    ratchet_triggered: false,
    secrecy_premium_flag: false,
    lti_vs_salary_ratio: 2.5
  },
  "DE0005439004": {
    company: "Continental AG",
    isin: "DE0005439004",
    exec_id: "Nikolai Setzer",
    year: 2024,
    cluster_id: 2,
    actual_pay: 4000000.0,
    cluster_median_pay: 3200000.0,
    multiple_of_median: 1.25,
    reach_ratio: 1.4,
    ratchet_triggered: false,
    secrecy_premium_flag: false,
    lti_vs_salary_ratio: 2.2
  }
};

export const PLACEHOLDER_ASSISTANT_REPLY =
  "The SML backend and Dual-Lens translator is initializing. If you see this, make sure the local FastAPI server is running on http://localhost:8000!";
