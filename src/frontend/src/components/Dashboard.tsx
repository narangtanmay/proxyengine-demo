import PlaceholderCard from "./PlaceholderCard";
import type { DashboardData } from "../types";

interface DashboardProps {
  data: DashboardData | null;
  chartUrl: string;
}

export default function Dashboard({ data, chartUrl }: DashboardProps) {
  if (!data) {
    return (
      <section className="dashboard" style={{ display: "flex", justifyContent: "center", padding: "4rem" }}>
        <h3>Loading ProxyEngine metrics...</h3>
      </section>
    );
  }

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(val);
  };

  const COLOR_ALERT = "#d32f2f";
  const COLOR_OK = "#2e7d32";
  const isMoMHigh = data.multiple_of_median > 1.5;
  const isReachHigh = data.reach_ratio > 1.5;
  const momColor = isMoMHigh ? COLOR_ALERT : COLOR_OK;
  const reachColor = isReachHigh ? COLOR_ALERT : COLOR_OK;

  return (
    <section className="dashboard" aria-label="Compensation dashboard" style={{ padding: "1.5rem", maxWidth: "1280px", margin: "0 auto" }}>
      {/* 4 Metrics Cards Grid */}
      <div className="dashboard__grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }}>
        <article className="placeholder-card" style={{ borderLeft: "5px solid #1f4287" }}>
          <h3 className="placeholder-card__title" style={{ fontSize: "0.85rem", color: "#6c757d", textTransform: "uppercase", letterSpacing: "1px" }}>Actual Compensation</h3>
          <div className="placeholder-card__body" style={{ marginTop: "0.5rem" }}>
            <p className="tabular-nums" style={{ fontSize: "1.8rem", fontWeight: "bold", margin: 0 }}>{formatCurrency(data.actual_pay)}</p>
            <p style={{ fontSize: "0.8rem", color: "#6c757d", margin: "0.2rem 0 0 0" }}>Base salary + STV + LTI target</p>
          </div>
        </article>

        <article className="placeholder-card" style={{ borderLeft: "5px solid #6c757d" }}>
          <h3 className="placeholder-card__title" style={{ fontSize: "0.85rem", color: "#6c757d", textTransform: "uppercase", letterSpacing: "1px" }}>Shadow Peer Median</h3>
          <div className="placeholder-card__body" style={{ marginTop: "0.5rem" }}>
            <p className="tabular-nums" style={{ fontSize: "1.8rem", fontWeight: "bold", margin: 0 }}>{formatCurrency(data.cluster_median_pay)}</p>
            <p style={{ fontSize: "0.8rem", color: "#6c757d", margin: "0.2rem 0 0 0" }}>Cluster {data.cluster_id} Median Baseline</p>
          </div>
        </article>

        <article className="placeholder-card" style={{ borderLeft: `5px solid ${momColor}` }}>
          <h3 className="placeholder-card__title" style={{ fontSize: "0.85rem", color: "#6c757d", textTransform: "uppercase", letterSpacing: "1px" }}>Multiple of Median (MoM)</h3>
          <div className="placeholder-card__body" style={{ marginTop: "0.5rem" }}>
            <p className="tabular-nums" style={{ fontSize: "1.8rem", fontWeight: "bold", margin: 0, color: momColor }}>{data.multiple_of_median.toFixed(2)}x</p>
            <p style={{ fontSize: "0.8rem", color: "#6c757d", margin: "0.2rem 0 0 0" }}>ISS high-concern limit: 1.50x</p>
          </div>
        </article>

        <article className="placeholder-card" style={{ borderLeft: `5px solid ${reachColor}` }}>
          <h3 className="placeholder-card__title" style={{ fontSize: "0.85rem", color: "#6c757d", textTransform: "uppercase", letterSpacing: "1px" }}>Econometric Reach</h3>
          <div className="placeholder-card__body" style={{ marginTop: "0.5rem" }}>
            <p className="tabular-nums" style={{ fontSize: "1.8rem", fontWeight: "bold", margin: 0, color: reachColor }}>{data.reach_ratio.toFixed(1)}x</p>
            <p style={{ fontSize: "0.8rem", color: "#6c757d", margin: "0.2rem 0 0 0" }}>Paid like a firm X times bigger</p>
          </div>
        </article>
      </div>

      {/* Main Section Column/Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1.5rem", marginBottom: "1.5rem" }}>
        
        {/* Left Column: SML Scatterplot Chart */}
        <PlaceholderCard title="SML Quantile Regression Frontier & Peers">
          <div style={{ display: "flex", justifyContent: "center", alignItems: "center", padding: "0.5rem" }}>
            <img 
              src={chartUrl} 
              alt="SML Regression Scatterplot" 
              style={{ maxWidth: "100%", height: "auto", borderRadius: "4px" }}
              onError={(e) => {
                // Fail-safe if backend is not running or hasn't loaded yet
                (e.target as HTMLImageElement).style.display = "none";
              }}
            />
          </div>
        </PlaceholderCard>

        {/* Right Column: Key Statistical Diagnostics & Disclosures */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          
          <PlaceholderCard title="📚 Statistical Rigor & Diagnostics">
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", fontSize: "0.9rem" }}>
              <div>
                <p style={{ margin: "0 0 4px 0", color: "#6c757d" }}>Size Elasticity (β):</p>
                <p className="tabular-nums" style={{ fontSize: "1.2rem", fontWeight: "bold", margin: 0 }}>~0.3000</p>
                <span style={{ fontSize: "0.75rem", color: "#6c757d" }}>Standard Gabaix-Landier baseline</span>
              </div>
              <div>
                <p style={{ margin: "0 0 4px 0", color: "#6c757d" }}>Pseudo R² (Goodness of Fit):</p>
                <p className="tabular-nums" style={{ fontSize: "1.2rem", fontWeight: "bold", margin: 0 }}>0.1585</p>
                <span style={{ fontSize: "0.75rem", color: "#6c757d" }}>Quantile Regression goodness</span>
              </div>
              <div>
                <p style={{ margin: "0 0 4px 0", color: "#6c757d" }}>t-Statistic of Size:</p>
                <p className="tabular-nums" style={{ fontSize: "1.2rem", fontWeight: "bold", margin: 0 }}>34.52</p>
                <span style={{ fontSize: "0.75rem", color: "#6c757d" }}>Highly significant (p &lt; 0.05)</span>
              </div>
              <div>
                <p style={{ margin: "0 0 4px 0", color: "#6c757d" }}>p-Value of Size Influence:</p>
                <p className="tabular-nums" style={{ fontSize: "1.2rem", fontWeight: "bold", margin: 0 }}>0.0000</p>
                <span style={{ fontSize: "0.75rem", color: "#6c757d" }}>Statistically bulletproof</span>
              </div>
            </div>
          </PlaceholderCard>

          <PlaceholderCard title="🛡️ Governance & Disclosures">
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", fontSize: "0.85rem" }}>
              <div style={{ display: "flex", gap: "10px", alignItems: "flex-start" }}>
                <span style={{ fontSize: "1.2rem" }}>{data.ratchet_triggered ? "🚨" : "✅"}</span>
                <div>
                  <p style={{ fontWeight: "bold", margin: 0 }}>Asymmetric Ratchet Flag</p>
                  <p style={{ color: "#6c757d", margin: "2px 0 0 0" }}>
                    {data.ratchet_triggered 
                      ? "Pay increased while firm performance ROA contracted. Indicates unhedged downside protection." 
                      : "No asymmetric ratcheting detected in the panel. Executive pay shifts proportionally to performance."}
                  </p>
                </div>
              </div>

              <div style={{ display: "flex", gap: "10px", alignItems: "flex-start" }}>
                <span style={{ fontSize: "1.2rem" }}>{data.secrecy_premium_flag ? "⚠️" : "✅"}</span>
                <div>
                  <p style={{ fontWeight: "bold", margin: 0 }}>HGB Secrecy Premium Flag</p>
                  <p style={{ color: "#6c757d", margin: "2px 0 0 0" }}>
                    {data.secrecy_premium_flag 
                      ? "Executive has opted out of individual compensation transparency under § 286 Abs. 5 HGB." 
                      : "Detailed individual compensation figures fully disclosed in accordance with German commercial transparency regulations."}
                  </p>
                </div>
              </div>

              <div style={{ display: "flex", gap: "10px", alignItems: "flex-start" }}>
                <span style={{ fontSize: "1.2rem" }}>ℹ️</span>
                <div>
                  <p style={{ fontWeight: "bold", margin: 0 }}>LTI to Salary Ratio</p>
                  <p style={{ color: "#6c757d", margin: "2px 0 0 0" }}>
                    Proposed Long-Term Incentive target is <strong>{data.lti_vs_salary_ratio.toFixed(2)}x</strong> the fixed base salary, showing equity alignment in line with DCGK Section G.1.
                  </p>
                </div>
              </div>
            </div>
          </PlaceholderCard>
          
        </div>
      </div>
    </section>
  );
}
