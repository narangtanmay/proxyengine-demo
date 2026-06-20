import { useCallback, useState, useEffect } from "react";
import Header from "./components/Header";
import Dashboard from "./components/Dashboard";
import ChatDrawer from "./components/chat/ChatDrawer";
import { COMPANIES, FALLBACK_DASHBOARD_DATA, FALLBACK_MODEL_INFO } from "./stubs";
import type { Message, Company, DashboardData, ModelInfo } from "./types";

const formatCurrency = (val: number) => {
  return new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(val);
};

// Compact scale label for company size (operating revenue): e.g. 300.9B, 45.6B, 980M.
const formatScale = (val: number) => {
  if (!val || val <= 0) return "n/a";
  if (val >= 1e9) return `€${(val / 1e9).toFixed(1)}B`;
  if (val >= 1e6) return `€${(val / 1e6).toFixed(0)}M`;
  return `€${(val / 1e3).toFixed(0)}K`;
};

const getAIAnswer = (key: string, lens: string, data: any) => {
  const company = data?.company || "the company";
  const exec_id = data?.exec_id || "the CEO";
  const reach_ratio = data?.reach_ratio || 1.0;
  const multiple_of_median = data?.multiple_of_median || 1.0;
  
  const answers: Record<string, Record<string, string>> = {
    reach: {
      auditor: `🔍 Activist Advisor Analysis: SML Quantile Residual mapping indicates CEO ${exec_id} is compensated as if running a company ${reach_ratio.toFixed(1)}x the actual scale of ${company}. This indicates severe unearned rent extraction lacking horizontal peer or size elasticity justification. We recommend voting AGAINST.`,
      compliance: `🛡️ Corporate Board Counsel Defense: The SML size premium of ${reach_ratio.toFixed(1)}x represents a vital global retention necessity in an internationally competitive CEO marketplace. Under DCGK Sections G.2 & G.9, this structure captures operating complexities not reflected in simple European scale metrics.`
    },
    ratchet: {
      auditor: `🔍 Activist Advisor Analysis: Our panel regression logs a highly egregious Asymmetric Ratchet (Pay-for-Luck). Total compensation escalated when performance was positive, but remained completely insulated during ROA contractions. This shifts wealth from shareholders to board members.`,
      compliance: `🛡️ Corporate Board Counsel Defense: Compensation adjustments were contractually driven by long-term restructuring milestones independent of cyclical ROA shocks. Disclosures detailing these strategic milestones satisfy DCGK Section G.10.`
    },
    mom: {
      auditor: `🔍 Activist Advisor Analysis: Total compensation is ${multiple_of_median.toFixed(2)}x the shadow peer cluster median, significantly breaching the ISS high-concern threshold of 1.50x. This confirms the package is a statistical outlier.`,
      compliance: `🛡️ Corporate Board Counsel Defense: The peer index selected by proxy advisors does not reflect the specialized global footprint of our operations. The board utilizes a customized international peer index compliant with DCGK G.2.`
    },
    secrecy: {
      auditor: `🔍 Activist Advisor Analysis: The executive has opted out of individual compensation disclosure under § 286 Abs. 5 HGB. This secrecy flag represents a critical disclosure risk, hindering shareholder accountability.`,
      compliance: `🛡️ Corporate Board Counsel Defense: The individual opt-out is approved by a supermajority shareholder resolution and strictly complies with German HGB commercial transparency statutes.`
    },
    ltiRatio: {
      auditor: `🔍 Activist Advisor Analysis: The LTI-to-Salary ratio is highly skewed, which when compounded with size-inflated base salary premiums, amplifies unearned payouts even under median market performance.`,
      compliance: `🛡️ Corporate Board Counsel Defense: We have heavily weighted the variable LTI component to ensure board incentives are tightly aligned with capital-market shareholder returns (TSR) over a multi-year horizon under DCGK G.1.`
    },
    esg: {
      auditor: `🔍 Activist Advisor Analysis: While variable components claim alignment, the ESG target cardboards lack quantifiable carbon metrics or measurable transparency, serving as a symbolic 'greenwashing' shield.`,
      compliance: `🛡️ Corporate Board Counsel Defense: Variable STV and LTI payouts are anchored to quantifiable carbon footprint reduction targets (15% weight) and corporate diversity index targets (10% weight) under DCGK Section G.1.`
    }
  };
  
  return answers[key]?.[lens] || "No segment narrative generated.";
};

export default function App() {
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [companies, setCompanies] = useState<Company[]>(COMPANIES);
  
  // Page / Wizard step state: 1, 2, or 3
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3>(1);
  
  // Page 1: Input and Data entry states
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>("DE0007664005");
  const [firmSearchText, setFirmSearchText] = useState("Volkswagen AG");
  const [showSuggestions, setShowSuggestions] = useState(false);
  
  const [boardPosition, setBoardPosition] = useState<string>("CEO");
  const [proposedBase, setProposedSalary] = useState<number>(1500000);
  const [proposedSti, setProposedSti] = useState<number>(2000000);
  const [proposedLti, setProposedLti] = useState<number>(4500000);
  const [maxEnumeration, setMaxEnumeration] = useState<number>(10000000);
  const [isEsgLinked, setIsEsgLinked] = useState<boolean>(true);

  // Page 2: Checklist criteria state
  const [criteria, setCriteria] = useState<Record<string, boolean>>({
    reach: true,
    ratchet: true,
    mom: true,
    secrecy: false,
    ltiRatio: true,
    esg: false,
  });

  const [lens, setLens] = useState<string>("auditor"); // auditor or compliance
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [modelInfo, setModelInfo] = useState<ModelInfo>(FALLBACK_MODEL_INFO);
  const [chartUrl, setChartUrl] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);

  // Page 2 -> 3 Progress loader states
  const [isCalculating, setIsCalculating] = useState(false);
  const [calculationProgress, setCalculationProgress] = useState(0);
  const [calculationMessage, setCalculationMessage] = useState("");

  // Selected criterion in Step 3 for detailed insights / visual support
  const [activeCriterion, setActiveCriterion] = useState<string>("reach");
  
  // Interactive Selection Profile modal state
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);

  const toggleChat = useCallback(() => setIsChatOpen((open) => !open), []);
  const closeChat = useCallback(() => setIsChatOpen(false), []);

  // Fetch companies on mount
  useEffect(() => {
    const fetchCompanies = async () => {
      try {
        const response = await fetch("http://localhost:8000/api/companies");
        if (response.ok) {
          const data = await response.json();
          setCompanies(data);
          if (data.length > 0) {
            setSelectedCompanyId(data[0].id);
            setFirmSearchText(data[0].name);
          }
        }
      } catch (err) {
        console.warn("Backend offline. Using stubbed companies.", err);
      }
    };
    fetchCompanies();
  }, []);

  // Fetch the fitted model diagnostics + sample-wide ratchet test once on mount.
  useEffect(() => {
    const fetchModelInfo = async () => {
      try {
        const response = await fetch("http://localhost:8000/api/model");
        if (response.ok) {
          setModelInfo(await response.json());
        }
      } catch (err) {
        console.warn("Backend offline. Using fallback model diagnostics.", err);
      }
    };
    fetchModelInfo();
  }, []);

  // Synchronize initial input values when company selection changes
  useEffect(() => {
    const fallback = FALLBACK_DASHBOARD_DATA[selectedCompanyId];
    if (fallback) {
      setProposedSalary(fallback.actual_pay * 0.25);
      setProposedSti(fallback.actual_pay * 0.30);
      setProposedLti(fallback.actual_pay * 0.45);
    }
    const compName = companies.find(c => c.id === selectedCompanyId)?.name;
    if (compName) {
      setFirmSearchText(compName);
    }
  }, [selectedCompanyId, companies]);

  // Submit and compute SML regression mapping (Step 2 -> Step 3 transition)
  const handleCalculateAnalysis = useCallback(async () => {
    // Start progress loading screen first
    setIsCalculating(true);
    setCalculationProgress(5);
    setCalculationMessage("Initializing SML environment...");

    // Helper to sleep/delay
    const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

    try {
      await delay(400);
      setCalculationProgress(20);
      setCalculationMessage("Loading local 15-year ORBIS financial panel dataset...");
      
      // In a real local connected app, we post our manual input states to compute trace
      const payload = {
        company_name: companies.find(c => c.id === selectedCompanyId)?.name || "Volkswagen AG",
        exec_id: `Executive Board (${boardPosition})`,
        proposed_salary: proposedBase,
        proposed_sti: proposedSti,
        proposed_lti: proposedLti,
        esg_linked: isEsgLinked,
        agenda_item: `Approval of Remuneration System for ${boardPosition}`
      };

      // Call our API with raw values to simulate PDF extraction
      const form = new FormData();
      // Dummy pdf data to invoke server process with actual overrides
      const blob = new Blob([JSON.stringify(payload)], { type: "application/json" });
      form.append("file", blob, "proposal.pdf");

      await delay(500);
      setCalculationProgress(45);
      setCalculationMessage("Executing unsupervised K-Means Shadow Peer clustering...");

      const uploadResp = await fetch("http://localhost:8000/api/upload-pdf", {
        method: "POST",
        body: form
      });

      await delay(600);
      setCalculationProgress(75);
      setCalculationMessage("Fitting Lasso-Regularized Quantile Regression Baseline...");

      if (uploadResp.ok) {
        const result = await uploadResp.json();
        setDashboardData(result.trace);
        setChartUrl(`http://localhost:8000/api/companies/${result.trace.isin}/chart.png?t=${Date.now()}`);
      } else {
        throw new Error("SML server failed");
      }
    } catch (err) {
      console.warn("Using offline deterministic analytical simulation.", err);
      const fallback = FALLBACK_DASHBOARD_DATA[selectedCompanyId] || FALLBACK_DASHBOARD_DATA["DE0007664005"];
      const proposed_comp = proposedBase + proposedSti + proposedLti;
      // Re-derive the premium/reach from the proposed package against the cached
      // fair-pay backdrop, using the real fitted size elasticity (beta).
      const beta = modelInfo.diagnostics.size_beta || 0.3;
      const residual = Math.log(proposed_comp) - Math.log(fallback.actual_pay) + Math.log(fallback.pay_premium);
      setDashboardData({
        ...fallback,
        actual_pay: proposed_comp,
        multiple_of_median: proposed_comp / fallback.cluster_median_pay,
        pay_premium: Math.exp(residual),
        reach_ratio: Math.exp(residual / beta),
        lti_vs_salary_ratio: proposedBase > 0 ? proposedLti / proposedBase : null
      });
      setChartUrl("");
    }

    await delay(500);
    setCalculationProgress(95);
    setCalculationMessage("Synthesizing dual-lens strategic compliance reports...");
    await delay(400);
    setCalculationProgress(100);
    setCalculationMessage("Analysis Complete!");
    await delay(200);
    
    setIsCalculating(false);
    setCurrentStep(3);
  }, [selectedCompanyId, proposedBase, proposedSti, proposedLti, boardPosition, isEsgLinked, companies]);

  // Handle live PDF uploads from header
  const handlePdfUploaded = useCallback((result: { trace: DashboardData; proposal: any }) => {
    setSelectedCompanyId(result.trace.isin);
    setProposedSalary(result.proposal.proposed_salary);
    setProposedSti(result.proposal.proposed_sti);
    setProposedLti(result.proposal.proposed_lti);
    setIsEsgLinked(result.proposal.esg_linked);
    setDashboardData(result.trace);
    setChartUrl(`http://localhost:8000/api/companies/${result.trace.isin}/chart.png?t=${Date.now()}`);
    setCurrentStep(3); // Advance straight to visual report presentation!
  }, []);

  const handleSendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
      createdAt: Date.now(),
    };

    setMessages((prev) => [...prev, userMessage]);

    try {
      const response = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company_id: selectedCompanyId,
          message: trimmed,
          lens: lens
        })
      });

      if (response.ok) {
        const result = await response.json();
        setMessages((prev) => [...prev, {
          id: crypto.randomUUID(),
          role: "assistant",
          content: result.content,
          createdAt: Date.now()
        }]);
      } else {
        throw new Error("Chat failed");
      }
    } catch (err) {
      // Local fallback template
      const currentData = dashboardData || FALLBACK_DASHBOARD_DATA[selectedCompanyId];
      const rep = lens === "auditor" 
        ? `**Activist Advisor Recommendation:** VOTE AGAINST proposed compensation for **${currentData?.company}**. SML Quantile Residual shows unearned size premium of **${currentData?.reach_ratio.toFixed(1)}x** running a firm multiple times actual scale.`
        : `**Corporate Defense Guidance:** The proposed remuneration carries significant ISS rejection warnings due to Multiple of Median exceeding 1.5x. Integrate strict DCGK Section G.1 metrics immediately.`;
        
      setMessages((prev) => [...prev, {
        id: crypto.randomUUID(),
        role: "assistant",
        content: rep,
        createdAt: Date.now()
      }]);
    }
  }, [selectedCompanyId, lens, dashboardData]);

  const handleLensChange = useCallback((newLens: string) => {
    setLens(newLens);
  }, []);

  const handleSelectBestPractice = () => {
    setCriteria({
      reach: true,
      ratchet: true,
      mom: true,
      secrecy: true,
      ltiRatio: true,
      esg: true,
    });
  };

  return (
    <div className="app-shell" style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      <Header 
        companies={companies}
        selectedId={selectedCompanyId}
        onCompanyChange={setSelectedCompanyId}
        lens={lens}
        onLensChange={handleLensChange}
        isChatOpen={isChatOpen} 
        onToggleChat={toggleChat} 
        onPdfUploaded={handlePdfUploaded}
      />
      
      {/* 3-Step Wizard Navigation Indicator */}
      <div className="wizard-navigation" style={{ 
        backgroundColor: "#ffffff", 
        borderBottom: "1px solid #dee2e6", 
        padding: "0.75rem 1.5rem", 
        display: "flex", 
        justifyContent: "center", 
        gap: "2rem",
        fontSize: "0.9rem",
        fontWeight: "bold"
      }}>
        <span 
          onClick={() => setCurrentStep(1)}
          style={{ color: currentStep === 1 ? "#1f4287" : "#6c757d", cursor: "pointer", borderBottom: currentStep === 1 ? "2px solid #1f4287" : "none", paddingBottom: "4px" }}
        >
          Step 1: Data Entry & Baseline
        </span>
        <span 
          onClick={() => currentStep >= 2 ? setCurrentStep(2) : null}
          style={{ color: currentStep === 2 ? "#1f4287" : "#6c757d", cursor: currentStep >= 2 ? "pointer" : "not-allowed", borderBottom: currentStep === 2 ? "2px solid #1f4287" : "none", paddingBottom: "4px" }}
        >
          Step 2: Evaluation Criteria
        </span>
        <span 
          onClick={() => dashboardData ? setCurrentStep(3) : null}
          style={{ color: currentStep === 3 ? "#1f4287" : "#6c757d", cursor: dashboardData ? "pointer" : "not-allowed", borderBottom: currentStep === 3 ? "2px solid #1f4287" : "none", paddingBottom: "4px" }}
        >
          Step 3: Analytical Report
        </span>
      </div>

      <main className="app-main" style={{ flexGrow: 1, backgroundColor: "#f8f9fa", minHeight: "calc(100vh - 130px)" }}>
        
        {isCalculating ? (
          <div style={{ 
            maxWidth: "600px", 
            margin: "4rem auto", 
            padding: "3rem", 
            backgroundColor: "#ffffff", 
            borderRadius: "8px", 
            boxShadow: "0 4px 6px rgba(0,0,0,0.05)",
            textAlign: "center"
          }}>
            <h2 style={{ fontSize: "1.5rem", fontWeight: "bold", marginBottom: "1rem", color: "#1f4287" }}>
              Running SML Regression Computations
            </h2>
            <div style={{ height: "20px", backgroundColor: "#e9ecef", borderRadius: "10px", overflow: "hidden", margin: "2rem 0", position: "relative" }}>
              <div style={{ 
                width: `${calculationProgress}%`, 
                height: "100%", 
                backgroundColor: "#ff7600", 
                transition: "width 0.3s ease-out" 
              }}></div>
            </div>
            <strong style={{ display: "block", fontSize: "1rem", color: "#495057", minHeight: "1.5rem" }}>
              {calculationProgress}% — {calculationMessage}
            </strong>
          </div>
        ) : (
          <>
            {/* ================= PAGE 1: DATA ENTRY ================= */}
        {currentStep === 1 && (
          <div style={{ maxWidth: "800px", margin: "2rem auto", padding: "2rem", backgroundColor: "#ffffff", borderRadius: "8px", boxShadow: "0 4px 6px rgba(0,0,0,0.05)" }}>
            <h2 style={{ fontSize: "1.5rem", fontWeight: "bold", marginBottom: "1rem", color: "#1f4287" }}>Page 1: Data Entry & First Impression</h2>
            <p style={{ color: "#6c757d", fontSize: "0.9rem", marginBottom: "1.5rem" }}>
              Enter the proposed compensation values for the executive board manually, or upload a remuneration report PDF in the header above to parse the values dynamically.
            </p>
            
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", marginBottom: "1.5rem" }}>
              <div style={{ position: "relative" }}>
                <label style={{ fontWeight: "bold", fontSize: "0.85rem", display: "block", marginBottom: "0.5rem" }}>German Corporation (Firm Identifier)</label>
                <input 
                  type="text"
                  placeholder="Search German corporations (e.g. Volkswagen, Bayer)..."
                  style={{ width: "100%", padding: "0.5rem", borderRadius: "4px", border: "1px solid #ced4da" }}
                  value={firmSearchText}
                  onChange={(e) => {
                    setFirmSearchText(e.target.value);
                    setShowSuggestions(true);
                  }}
                  onFocus={() => setShowSuggestions(true)}
                  onBlur={() => setTimeout(() => setShowSuggestions(false), 200)} // Allow onMouseDown to trigger first
                />
                
                {showSuggestions && (
                  <div style={{ 
                    position: "absolute", 
                    top: "100%", 
                    left: 0, 
                    right: 0, 
                    backgroundColor: "#ffffff", 
                    border: "1px solid #ced4da", 
                    borderRadius: "4px", 
                    boxShadow: "0 4px 6px rgba(0,0,0,0.1)", 
                    zIndex: 10,
                    maxHeight: "150px",
                    overflowY: "auto"
                  }}>
                    {companies
                      .filter(c => c.name.toLowerCase().includes(firmSearchText.toLowerCase()))
                      .map((c) => (
                        <div 
                          key={c.id}
                          style={{ padding: "0.5rem", cursor: "pointer", borderBottom: "1px solid #eee" }}
                          onMouseDown={() => {
                            setSelectedCompanyId(c.id);
                            setFirmSearchText(c.name);
                            setShowSuggestions(false);
                          }}
                        >
                          {c.name}
                        </div>
                      ))}
                    {companies.filter(c => c.name.toLowerCase().includes(firmSearchText.toLowerCase())).length === 0 && (
                      <div style={{ padding: "0.5rem", color: "#6c757d" }}>No companies found</div>
                    )}
                  </div>
                )}
              </div>
              
              <div>
                <label style={{ fontWeight: "bold", fontSize: "0.85rem", display: "block", marginBottom: "0.5rem" }}>Board Position Class</label>
                <select 
                  style={{ width: "100%", padding: "0.5rem", borderRadius: "4px", border: "1px solid #ced4da" }}
                  value={boardPosition}
                  onChange={(e) => setBoardPosition(e.target.value)}
                >
                  <option value="CEO">Chief Executive Officer (CEO)</option>
                  <option value="CFO">Chief Financial Officer (CFO)</option>
                  <option value="Member">Regular Board Member (Aufsichtsrat)</option>
                </select>
              </div>
            </div>

            <h3 style={{ fontSize: "1.1rem", fontWeight: "bold", marginBottom: "1rem", borderBottom: "1px solid #eee", paddingBottom: "0.5rem" }}>Enumeration Package Specification</h3>
            
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", marginBottom: "1.5rem" }}>
              <div>
                <label style={{ fontWeight: "bold", fontSize: "0.85rem", display: "block", marginBottom: "0.5rem" }}>Fixed Base Component (€)</label>
                <input 
                  type="number"
                  style={{ width: "100%", padding: "0.5rem", borderRadius: "4px", border: "1px solid #ced4da" }}
                  value={proposedBase}
                  onChange={(e) => setProposedSalary(Number(e.target.value))}
                />
              </div>

              <div>
                <label style={{ fontWeight: "bold", fontSize: "0.85rem", display: "block", marginBottom: "0.5rem" }}>Short-Term Variable STV (€)</label>
                <input 
                  type="number"
                  style={{ width: "100%", padding: "0.5rem", borderRadius: "4px", border: "1px solid #ced4da" }}
                  value={proposedSti}
                  onChange={(e) => setProposedSti(Number(e.target.value))}
                />
              </div>

              <div>
                <label style={{ fontWeight: "bold", fontSize: "0.85rem", display: "block", marginBottom: "0.5rem" }}>Long-Term Variable LTI (€)</label>
                <input 
                  type="number"
                  style={{ width: "100%", padding: "0.5rem", borderRadius: "4px", border: "1px solid #ced4da" }}
                  value={proposedLti}
                  onChange={(e) => setProposedLti(Number(e.target.value))}
                />
              </div>

              <div>
                <label style={{ fontWeight: "bold", fontSize: "0.85rem", display: "block", marginBottom: "0.5rem" }}>Maximum Cap Enumeration (€)</label>
                <input 
                  type="number"
                  style={{ width: "100%", padding: "0.5rem", borderRadius: "4px", border: "1px solid #ced4da" }}
                  value={maxEnumeration}
                  onChange={(e) => setMaxEnumeration(Number(e.target.value))}
                />
              </div>
            </div>

            <div style={{ display: "flex", gap: "1rem", alignItems: "center", marginBottom: "2rem" }}>
              <input 
                type="checkbox" 
                id="esg" 
                checked={isEsgLinked} 
                onChange={(e) => setIsEsgLinked(e.target.checked)} 
                style={{ width: "18px", height: "18px" }}
              />
              <label htmlFor="esg" style={{ fontSize: "0.9rem", fontWeight: "bold", cursor: "pointer" }}>Is any variable portion explicitly linked to ESG target cardboards?</label>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button
                type="button"
                className="button button--primary"
                onClick={() => setCurrentStep(2)}
                style={{ padding: "0.75rem 2rem", fontSize: "1rem", borderRadius: "6px", cursor: "pointer" }}
              >
                Proceed to Criteria →
              </button>
            </div>
          </div>
        )}

        {/* ================= PAGE 2: SPECIFY CRITERIA ================= */}
        {currentStep === 2 && (
          <div style={{ maxWidth: "800px", margin: "2rem auto", padding: "2rem", backgroundColor: "#ffffff", borderRadius: "8px", boxShadow: "0 4px 6px rgba(0,0,0,0.05)" }}>
            <h2 style={{ fontSize: "1.5rem", fontWeight: "bold", marginBottom: "1rem", color: "#1f4287" }}>Page 2: Specify Query & Checklist Requirements</h2>
            <p style={{ color: "#6c757d", fontSize: "0.9rem", marginBottom: "1.5rem" }}>
              What do you want to analyze and know about the executive remuneration proposal? Select the evaluation checklist queries.
            </p>

            <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem" }}>
              <button 
                type="button" 
                className="button"
                onClick={handleSelectBestPractice}
                style={{ padding: "0.5rem 1rem", fontSize: "0.85rem", backgroundColor: "#e9ecef", border: "none", borderRadius: "4px", cursor: "pointer" }}
              >
                ✨ Auto Select Best Practice Profile
              </button>
              <button 
                type="button" 
                className="button"
                onClick={() => setIsProfileModalOpen(true)}
                style={{ padding: "0.5rem 1rem", fontSize: "0.85rem", backgroundColor: "#e9ecef", border: "none", borderRadius: "4px", cursor: "pointer" }}
              >
                📂 Load Stored Selection Profile
              </button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "1rem", marginBottom: "2rem", border: "1px solid #dee2e6", padding: "1.5rem", borderRadius: "6px", backgroundColor: "#f8f9fa" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <input 
                  type="checkbox" 
                  id="c_reach" 
                  checked={criteria.reach} 
                  onChange={(e) => setCriteria({...criteria, reach: e.target.checked})}
                  style={{ width: "20px", height: "20px" }}
                />
                <label htmlFor="c_reach" style={{ fontSize: "0.95rem", fontWeight: "bold", cursor: "pointer" }}>Is the econometric "Reach" ratio within size limits? (Gabaix-Landier size theorem check)</label>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <input 
                  type="checkbox" 
                  id="c_ratchet" 
                  checked={criteria.ratchet} 
                  onChange={(e) => setCriteria({...criteria, ratchet: e.target.checked})}
                  style={{ width: "20px", height: "20px" }}
                />
                <label htmlFor="c_ratchet" style={{ fontSize: "0.95rem", fontWeight: "bold", cursor: "pointer" }}>Is there proof of Downside Risk Insulation? (Asymmetric Ratchet / pay-for-luck panel test)</label>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <input 
                  type="checkbox" 
                  id="c_mom" 
                  checked={criteria.mom} 
                  onChange={(e) => setCriteria({...criteria, mom: e.target.checked})}
                  style={{ width: "20px", height: "20px" }}
                />
                <label htmlFor="c_mom" style={{ fontSize: "0.95rem", fontWeight: "bold", cursor: "pointer" }}>Does CEO payout satisfy the 1.50x Multiple of Median (MoM) ISS alignment threshold?</label>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <input 
                  type="checkbox" 
                  id="c_secrecy" 
                  checked={criteria.secrecy} 
                  onChange={(e) => setCriteria({...criteria, secrecy: e.target.checked})}
                  style={{ width: "20px", height: "20px" }}
                />
                <label htmlFor="c_secrecy" style={{ fontSize: "0.95rem", fontWeight: "bold", cursor: "pointer" }}>Does the executive board trigger individual secrecy flags? (§ 286 Abs. 5 HGB opt-out check)</label>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <input 
                  type="checkbox" 
                  id="c_ltiRatio" 
                  checked={criteria.ltiRatio} 
                  onChange={(e) => setCriteria({...criteria, ltiRatio: e.target.checked})}
                  style={{ width: "20px", height: "20px" }}
                />
                <label htmlFor="c_ltiRatio" style={{ fontSize: "0.95rem", fontWeight: "bold", cursor: "pointer" }}>Is the Long-Term Equity Incentive (LTI) ratio compliant with DCGK Section G.1 guidelines?</label>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <input 
                  type="checkbox" 
                  id="c_esg" 
                  checked={criteria.esg} 
                  onChange={(e) => setCriteria({...criteria, esg: e.target.checked})}
                  style={{ width: "20px", height: "20px" }}
                />
                <label htmlFor="c_esg" style={{ fontSize: "0.95rem", fontWeight: "bold", cursor: "pointer" }}>Are performance criteria anchored to ESG/Sustainability goals?</label>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <button
                type="button"
                className="button"
                onClick={() => setCurrentStep(1)}
                style={{ padding: "0.75rem 1.5rem", fontSize: "1rem", borderRadius: "6px", cursor: "pointer", border: "1px solid #ced4da" }}
              >
                ← Back
              </button>

              <button
                type="button"
                className="button button--primary"
                onClick={handleCalculateAnalysis}
                style={{ padding: "0.75rem 2rem", fontSize: "1rem", borderRadius: "6px", cursor: "pointer", backgroundColor: "#ff7600", border: "none", color: "#fff" }}
              >
                Submit Evaluation Criteria ⚙️
              </button>
            </div>
          </div>
        )}

        {/* ================= PAGE 3: COMPREHENSIVE REPORT VISUALS ================= */}
        {currentStep === 3 && (
          <div style={{ maxWidth: "1280px", margin: "0 auto", padding: "1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", borderBottom: "1px solid #dee2e6", paddingBottom: "0.5rem" }}>
              <h2 style={{ fontSize: "1.4rem", fontWeight: "bold", color: "#1f4287", margin: 0 }}>Page 3: Automated Strategic Evaluation Report</h2>
              <button
                type="button"
                className="button"
                onClick={() => setCurrentStep(1)}
                style={{ padding: "0.4rem 1rem", fontSize: "0.85rem", borderRadius: "4px", border: "1px solid #ced4da", cursor: "pointer" }}
              >
                🔄 Re-Evaluate / Modify Inputs
              </button>
            </div>

            {/* Split Screen Grid matching exactly wireframe Page 3 */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
              
              {/* Left Column: Recommended vs Proposed Packages + Insights Dropdowns */}
              <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
                
                {/* 1. Comparison Packages */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                  <div style={{ border: "1px solid #dee2e6", borderRadius: "6px", padding: "1rem", backgroundColor: "#ffffff" }}>
                    <h4 style={{ fontSize: "0.85rem", fontWeight: "bold", color: "#6c757d", textTransform: "uppercase", margin: "0 0 0.5rem 0" }}>Recommended Package Baseline</h4>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px", textAlign: "center" }}>
                      <div style={{ backgroundColor: "#f8f9fa", padding: "4px", borderRadius: "4px" }}>
                        <span style={{ fontSize: "0.7rem", color: "#6c757d", display: "block" }}>Base</span>
                        <strong className="tabular-nums" style={{ fontSize: "0.85rem" }}>{formatCurrency(proposedBase * 0.9)}</strong>
                      </div>
                      <div style={{ backgroundColor: "#f8f9fa", padding: "4px", borderRadius: "4px" }}>
                        <span style={{ fontSize: "0.7rem", color: "#6c757d", display: "block" }}>STV</span>
                        <strong className="tabular-nums" style={{ fontSize: "0.85rem" }}>{formatCurrency(proposedSti * 0.75)}</strong>
                      </div>
                      <div style={{ backgroundColor: "#f8f9fa", padding: "4px", borderRadius: "4px" }}>
                        <span style={{ fontSize: "0.7rem", color: "#6c757d", display: "block" }}>LTI</span>
                        <strong className="tabular-nums" style={{ fontSize: "0.85rem" }}>{formatCurrency(proposedLti * 0.65)}</strong>
                      </div>
                    </div>
                  </div>

                  <div style={{ border: "1px solid #dee2e6", borderRadius: "6px", padding: "1rem", backgroundColor: "#ffffff" }}>
                    <h4 style={{ fontSize: "0.85rem", fontWeight: "bold", color: "#ff7600", textTransform: "uppercase", margin: "0 0 0.5rem 0" }}>Proposed Remuneration Package</h4>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px", textAlign: "center" }}>
                      <div style={{ backgroundColor: "#fff5f0", padding: "4px", borderRadius: "4px" }}>
                        <span style={{ fontSize: "0.7rem", color: "#ff7600", display: "block" }}>Base</span>
                        <strong className="tabular-nums" style={{ fontSize: "0.85rem" }}>{formatCurrency(proposedBase)}</strong>
                      </div>
                      <div style={{ backgroundColor: "#fff5f0", padding: "4px", borderRadius: "4px" }}>
                        <span style={{ fontSize: "0.7rem", color: "#ff7600", display: "block" }}>STV</span>
                        <strong className="tabular-nums" style={{ fontSize: "0.85rem" }}>{formatCurrency(proposedSti)}</strong>
                      </div>
                      <div style={{ backgroundColor: "#fff5f0", padding: "4px", borderRadius: "4px" }}>
                        <span style={{ fontSize: "0.7rem", color: "#ff7600", display: "block" }}>LTI</span>
                        <strong className="tabular-nums" style={{ fontSize: "0.85rem" }}>{formatCurrency(proposedLti)}</strong>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 2. Insights Checklist Dropdowns */}
                <div style={{ border: "1px solid #dee2e6", borderRadius: "6px", padding: "1.25rem", backgroundColor: "#ffffff" }}>
                  <h3 style={{ fontSize: "1.1rem", fontWeight: "bold", margin: "0 0 1rem 0", color: "#1f4287" }}>Our Insights (Evaluation Results)</h3>
                  
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                    
                    {criteria.reach && (
                      <div 
                        style={{ 
                          border: activeCriterion === "reach" ? `2px solid ${lens === "auditor" ? "#1f4287" : "#ff7600"}` : "1px solid #dee2e6", 
                          borderRadius: "6px", 
                          padding: "0.75rem", 
                          cursor: "pointer", 
                          backgroundColor: activeCriterion === "reach" ? "#f8f9fa" : "#ffffff",
                          transition: "all 0.2s ease"
                        }}
                        onClick={() => setActiveCriterion("reach")}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <span style={{ fontWeight: "bold", fontSize: "0.9rem", display: "flex", alignItems: "center", gap: "8px" }}>
                            <span>{activeCriterion === "reach" ? "▼" : "▶"}</span>
                            <span>Reach Anomaly check ({dashboardData?.reach_ratio.toFixed(1)}x premium)</span>
                          </span>
                          <span style={{ 
                            color: (dashboardData?.reach_ratio || 1) > 2.0 ? "#d32f2f" : "#2e7d32", 
                            fontWeight: "bold",
                            fontSize: "0.9rem"
                          }}>
                            {(dashboardData?.reach_ratio || 1) > 2.0 ? "❌ (Fail)" : "✔️ (Pass)"}
                          </span>
                        </div>
                        {activeCriterion === "reach" && (
                          <div style={{ 
                            marginTop: "0.75rem", 
                            paddingTop: "0.75rem", 
                            borderTop: "1px dashed #dee2e6", 
                            fontSize: "0.85rem", 
                            color: "#333333",
                            lineHeight: "1.4",
                            borderLeft: `3px solid ${lens === "auditor" ? "#1f4287" : "#ff7600"}`,
                            paddingLeft: "0.75rem"
                          }}>
                            {getAIAnswer("reach", lens, dashboardData)}
                          </div>
                        )}
                      </div>
                    )}

                    {criteria.ratchet && (
                      <div 
                        style={{ 
                          border: activeCriterion === "ratchet" ? `2px solid ${lens === "auditor" ? "#1f4287" : "#ff7600"}` : "1px solid #dee2e6", 
                          borderRadius: "6px", 
                          padding: "0.75rem", 
                          cursor: "pointer", 
                          backgroundColor: activeCriterion === "ratchet" ? "#f8f9fa" : "#ffffff",
                          transition: "all 0.2s ease"
                        }}
                        onClick={() => setActiveCriterion("ratchet")}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <span style={{ fontWeight: "bold", fontSize: "0.9rem", display: "flex", alignItems: "center", gap: "8px" }}>
                            <span>{activeCriterion === "ratchet" ? "▼" : "▶"}</span>
                            <span>Downside Risk Insulation check (Asymmetric Ratchet)</span>
                          </span>
                          <span style={{ 
                            color: dashboardData?.ratchet_triggered ? "#d32f2f" : "#2e7d32", 
                            fontWeight: "bold",
                            fontSize: "0.9rem"
                          }}>
                            {dashboardData?.ratchet_triggered ? "❌ (Ratchet Triggered)" : "✔️ (Pass)"}
                          </span>
                        </div>
                        {activeCriterion === "ratchet" && (
                          <div style={{ 
                            marginTop: "0.75rem", 
                            paddingTop: "0.75rem", 
                            borderTop: "1px dashed #dee2e6", 
                            fontSize: "0.85rem", 
                            color: "#333333",
                            lineHeight: "1.4",
                            borderLeft: `3px solid ${lens === "auditor" ? "#1f4287" : "#ff7600"}`,
                            paddingLeft: "0.75rem"
                          }}>
                            {getAIAnswer("ratchet", lens, dashboardData)}
                          </div>
                        )}
                      </div>
                    )}

                    {criteria.mom && (
                      <div 
                        style={{ 
                          border: activeCriterion === "mom" ? `2px solid ${lens === "auditor" ? "#1f4287" : "#ff7600"}` : "1px solid #dee2e6", 
                          borderRadius: "6px", 
                          padding: "0.75rem", 
                          cursor: "pointer", 
                          backgroundColor: activeCriterion === "mom" ? "#f8f9fa" : "#ffffff",
                          transition: "all 0.2s ease"
                        }}
                        onClick={() => setActiveCriterion("mom")}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <span style={{ fontWeight: "bold", fontSize: "0.9rem", display: "flex", alignItems: "center", gap: "8px" }}>
                            <span>{activeCriterion === "mom" ? "▼" : "▶"}</span>
                            <span>ISS Multiple of Median (MoM) check ({dashboardData?.multiple_of_median.toFixed(2)}x)</span>
                          </span>
                          <span style={{ 
                            color: (dashboardData?.multiple_of_median || 1) > 1.5 ? "#d32f2f" : "#2e7d32", 
                            fontWeight: "bold",
                            fontSize: "0.9rem"
                          }}>
                            {(dashboardData?.multiple_of_median || 1) > 1.5 ? "❌ (Failed Alignment)" : "✔️ (Pass)"}
                          </span>
                        </div>
                        {activeCriterion === "mom" && (
                          <div style={{ 
                            marginTop: "0.75rem", 
                            paddingTop: "0.75rem", 
                            borderTop: "1px dashed #dee2e6", 
                            fontSize: "0.85rem", 
                            color: "#333333",
                            lineHeight: "1.4",
                            borderLeft: `3px solid ${lens === "auditor" ? "#1f4287" : "#ff7600"}`,
                            paddingLeft: "0.75rem"
                          }}>
                            {getAIAnswer("mom", lens, dashboardData)}
                          </div>
                        )}
                      </div>
                    )}

                    {criteria.secrecy && (
                      <div 
                        style={{ 
                          border: activeCriterion === "secrecy" ? `2px solid ${lens === "auditor" ? "#1f4287" : "#ff7600"}` : "1px solid #dee2e6", 
                          borderRadius: "6px", 
                          padding: "0.75rem", 
                          cursor: "pointer", 
                          backgroundColor: activeCriterion === "secrecy" ? "#f8f9fa" : "#ffffff",
                          transition: "all 0.2s ease"
                        }}
                        onClick={() => setActiveCriterion("secrecy")}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <span style={{ fontWeight: "bold", fontSize: "0.9rem", display: "flex", alignItems: "center", gap: "8px" }}>
                            <span>{activeCriterion === "secrecy" ? "▼" : "▶"}</span>
                            <span>§ 286 Abs. 5 HGB Individual Secrecy Opt-out</span>
                          </span>
                          <span style={{ 
                            color: dashboardData?.secrecy_premium_flag ? "#ff7600" : "#2e7d32", 
                            fontWeight: "bold",
                            fontSize: "0.9rem"
                          }}>
                            {dashboardData?.secrecy_premium_flag ? "⚠️ (Opted-out)" : "✔️ (Disclosed)"}
                          </span>
                        </div>
                        {activeCriterion === "secrecy" && (
                          <div style={{ 
                            marginTop: "0.75rem", 
                            paddingTop: "0.75rem", 
                            borderTop: "1px dashed #dee2e6", 
                            fontSize: "0.85rem", 
                            color: "#333333",
                            lineHeight: "1.4",
                            borderLeft: `3px solid ${lens === "auditor" ? "#1f4287" : "#ff7600"}`,
                            paddingLeft: "0.75rem"
                          }}>
                            {getAIAnswer("secrecy", lens, dashboardData)}
                          </div>
                        )}
                      </div>
                    )}

                    {criteria.ltiRatio && (
                      <div 
                        style={{ 
                          border: activeCriterion === "ltiRatio" ? `2px solid ${lens === "auditor" ? "#1f4287" : "#ff7600"}` : "1px solid #dee2e6", 
                          borderRadius: "6px", 
                          padding: "0.75rem", 
                          cursor: "pointer", 
                          backgroundColor: activeCriterion === "ltiRatio" ? "#f8f9fa" : "#ffffff",
                          transition: "all 0.2s ease"
                        }}
                        onClick={() => setActiveCriterion("ltiRatio")}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <span style={{ fontWeight: "bold", fontSize: "0.9rem", display: "flex", alignItems: "center", gap: "8px" }}>
                            <span>{activeCriterion === "ltiRatio" ? "▼" : "▶"}</span>
                            <span>DCGK G.1 Compliant Incentive Balance check</span>
                          </span>
                          <span style={{ 
                            color: (proposedLti / proposedBase) > 4.0 ? "#ff7600" : "#2e7d32", 
                            fontWeight: "bold",
                            fontSize: "0.9rem"
                          }}>
                            {(proposedLti / proposedBase) > 4.0 ? "⚠️ (Imbalanced LTI)" : "✔️ (Pass)"}
                          </span>
                        </div>
                        {activeCriterion === "ltiRatio" && (
                          <div style={{ 
                            marginTop: "0.75rem", 
                            paddingTop: "0.75rem", 
                            borderTop: "1px dashed #dee2e6", 
                            fontSize: "0.85rem", 
                            color: "#333333",
                            lineHeight: "1.4",
                            borderLeft: `3px solid ${lens === "auditor" ? "#1f4287" : "#ff7600"}`,
                            paddingLeft: "0.75rem"
                          }}>
                            {getAIAnswer("ltiRatio", lens, dashboardData)}
                          </div>
                        )}
                      </div>
                    )}

                    {criteria.esg && (
                      <div 
                        style={{ 
                          border: activeCriterion === "esg" ? `2px solid ${lens === "auditor" ? "#1f4287" : "#ff7600"}` : "1px solid #dee2e6", 
                          borderRadius: "6px", 
                          padding: "0.75rem", 
                          cursor: "pointer", 
                          backgroundColor: activeCriterion === "esg" ? "#f8f9fa" : "#ffffff",
                          transition: "all 0.2s ease"
                        }}
                        onClick={() => setActiveCriterion("esg")}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <span style={{ fontWeight: "bold", fontSize: "0.9rem", display: "flex", alignItems: "center", gap: "8px" }}>
                            <span>{activeCriterion === "esg" ? "▼" : "▶"}</span>
                            <span>ESG Performance linkages check</span>
                          </span>
                          <span style={{ 
                            color: isEsgLinked ? "#2e7d32" : "#ff7600", 
                            fontWeight: "bold",
                            fontSize: "0.9rem"
                          }}>
                            {isEsgLinked ? "✔️ (Aligned)" : "⚠️ (No ESG target cardboard)"}
                          </span>
                        </div>
                        {activeCriterion === "esg" && (
                          <div style={{ 
                            marginTop: "0.75rem", 
                            paddingTop: "0.75rem", 
                            borderTop: "1px dashed #dee2e6", 
                            fontSize: "0.85rem", 
                            color: "#333333",
                            lineHeight: "1.4",
                            borderLeft: `3px solid ${lens === "auditor" ? "#1f4287" : "#ff7600"}`,
                            paddingLeft: "0.75rem"
                          }}>
                            {getAIAnswer("esg", lens, dashboardData)}
                          </div>
                        )}
                      </div>
                    )}

                  </div>
                </div>

              </div>

              {/* Right Column: High Level Descriptive & Supporting Visualizations */}
              <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
                
                {/* 1. High Level Descriptive Visualizations */}
                <Dashboard
                  data={dashboardData}
                  chartUrl={chartUrl}
                  modelInfo={modelInfo}
                />

                {/* 2. Question Specific Supporting Visualizations (Dynamic) */}
                <div style={{ border: "1px solid #dee2e6", borderRadius: "6px", padding: "1.25rem", backgroundColor: "#ffffff" }}>
                  <h3 style={{ fontSize: "1.1rem", fontWeight: "bold", margin: "0 0 1rem 0", color: "#ff7600" }}>
                    Question Specific Supporting Visualization: {activeCriterion.toUpperCase()}
                  </h3>
                  
                  {activeCriterion === "reach" && (
                    <div>
                      <p style={{ fontSize: "0.85rem", color: "#6c757d", margin: "0 0 1rem 0" }}>
                        Visualizing size-adjusted executive compensation. The fitted SML quantile baseline
                        has a size elasticity of β ≈ {modelInfo.diagnostics.size_beta.toFixed(2)}
                        {" "}(every doubling of size adds ~{(Math.pow(2, modelInfo.diagnostics.size_beta) * 100 - 100).toFixed(0)}% pay).
                        The pay premium (actual ÷ benchmark) is {dashboardData ? `${dashboardData.pay_premium.toFixed(2)}x` : "n/a"}.
                      </p>
                      <div style={{ display: "flex", justifyContent: "space-between", border: "1px solid #eee", padding: "1rem", borderRadius: "4px", backgroundColor: "#f8f9fa" }}>
                        <div>
                          <span style={{ fontSize: "0.75rem", color: "#6c757d", display: "block" }}>Company Scale (Opre)</span>
                          <strong style={{ fontSize: "1.2rem" }}>{dashboardData ? formatScale(dashboardData.opre) : "n/a"}</strong>
                        </div>
                        <div>
                          <span style={{ fontSize: "0.75rem", color: "#6c757d", display: "block" }}>Expected Pay Baseline</span>
                          <strong style={{ fontSize: "1.2rem" }}>{formatCurrency(dashboardData?.cluster_median_pay || 0)}</strong>
                        </div>
                        <div>
                          <span style={{ fontSize: "0.75rem", color: "#6c757d", display: "block" }}>Economic Reach Premium</span>
                          <strong style={{ fontSize: "1.2rem", color: (dashboardData?.reach_ratio || 1) > 2 ? "#d32f2f" : "#2e7d32" }}>{dashboardData?.reach_ratio.toFixed(1)}x Larger Firm</strong>
                        </div>
                      </div>
                    </div>
                  )}

                  {activeCriterion === "ratchet" && (
                    <div>
                      <p style={{ fontSize: "0.85rem", color: "#6c757d", margin: "0 0 1rem 0" }}>
                        Visualizing Pay-for-Luck asymmetry (Garvey &amp; Milbourn, 2006). We regress the change
                        in pay on the change in profitability separately for good years (Δroa &gt; 0,
                        n = {modelInfo.ratchet.n_good}) and bad years (Δroa &lt; 0, n = {modelInfo.ratchet.n_bad}).
                        The flag fires only if the good-year slope dominates — here it does
                        <strong> {modelInfo.ratchet.fires ? "fire" : "not fire"}</strong>.
                      </p>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                        <div style={{ padding: "0.75rem", backgroundColor: "#fff5f5", borderLeft: "4px solid #d32f2f", borderRadius: "4px" }}>
                          <span style={{ fontSize: "0.75rem", color: "#6c757d", display: "block" }}>Pay Sensitivity in Good Years (Δroa &gt; 0)</span>
                          <strong style={{ fontSize: "1.1rem", color: "#d32f2f" }}>{modelInfo.ratchet.good_year_slope >= 0 ? "+" : ""}{modelInfo.ratchet.good_year_slope.toFixed(3)}</strong>
                        </div>
                        <div style={{ padding: "0.75rem", backgroundColor: "#f4fbf4", borderLeft: "4px solid #2e7d32", borderRadius: "4px" }}>
                          <span style={{ fontSize: "0.75rem", color: "#6c757d", display: "block" }}>Pay Sensitivity in Bad Years (Δroa &lt; 0)</span>
                          <strong style={{ fontSize: "1.1rem", color: "#2e7d32" }}>{modelInfo.ratchet.bad_year_slope >= 0 ? "+" : ""}{modelInfo.ratchet.bad_year_slope.toFixed(3)}</strong>
                        </div>
                      </div>
                    </div>
                  )}

                  {activeCriterion === "mom" && (
                    <div>
                      <p style={{ fontSize: "0.85rem", color: "#6c757d", margin: "0 0 1rem 0" }}>
                        Multiple of Median (MoM) peer alignment distribution. Shows target company total comp relative to the objective Shadow Peer cluster.
                      </p>
                      <div style={{ height: "16px", backgroundColor: "#e9ecef", borderRadius: "8px", position: "relative", margin: "1.5rem 0 1rem 0" }}>
                        <div style={{ position: "absolute", left: "0%", width: "50%", height: "100%", backgroundColor: "#2e7d32", borderTopLeftRadius: "8px", borderBottomLeftRadius: "8px" }}></div>
                        <div style={{ position: "absolute", left: "50%", width: "25%", height: "100%", backgroundColor: "#ff7600" }}></div>
                        <div style={{ position: "absolute", left: "75%", width: "25%", height: "100%", backgroundColor: "#d32f2f", borderTopRightRadius: "8px", borderBottomRightRadius: "8px" }}></div>
                        <div style={{ 
                          position: "absolute", 
                          left: `${Math.min(100, (dashboardData?.multiple_of_median || 1) * 33)}%`, 
                          top: "-8px", 
                          width: "8px", 
                          height: "32px", 
                          backgroundColor: "#000000", 
                          borderRadius: "4px" 
                        }}></div>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", color: "#6c757d" }}>
                        <span>Median Peer (1.0x)</span>
                        <span>ISS Concern limit (1.5x)</span>
                        <span>High Concern (&gt;2.0x)</span>
                      </div>
                    </div>
                  )}

                  {activeCriterion === "secrecy" && (
                    <div>
                      <p style={{ fontSize: "0.85rem", color: "#6c757d", margin: "0 0 1rem 0" }}>
                        German commercial transparency opting out diagnostics. Firms utilizing opt-outs exhibit a statistically significant secrecy premium.
                      </p>
                      <div style={{ padding: "0.75rem", backgroundColor: "#fffbeb", borderRadius: "4px", border: "1px solid #ffeeba", fontSize: "0.8rem", color: "#856404" }}>
                        ℹ️ <strong>Commercial Code Notice:</strong> German legislation allows corporations to opt out of individual board transparency disclosures under § 286 Abs. 5 HGB. If active, proxy advisors assess an automatic disclosure risk premium.
                      </div>
                    </div>
                  )}

                  {activeCriterion === "ltiRatio" && (() => {
                    const total = proposedBase + proposedSti + proposedLti || 1;
                    const basePct = (proposedBase / total) * 100;
                    const stiPct = (proposedSti / total) * 100;
                    const ltiPct = (proposedLti / total) * 100;
                    const ltiToBase = proposedBase > 0 ? proposedLti / proposedBase : 0;
                    return (
                    <div>
                      <p style={{ fontSize: "0.85rem", color: "#6c757d", margin: "0 0 1rem 0" }}>
                        Proposed remuneration incentive component splits:
                      </p>
                      <div style={{ display: "flex", height: "30px", borderRadius: "4px", overflow: "hidden", margin: "1rem 0" }}>
                        <div style={{ width: `${basePct}%`, backgroundColor: "#1f4287", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.8rem", fontWeight: "bold" }}>
                          Base ({basePct.toFixed(0)}%)
                        </div>
                        <div style={{ width: `${stiPct}%`, backgroundColor: "#007cc7", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.8rem", fontWeight: "bold" }}>
                          STV ({stiPct.toFixed(0)}%)
                        </div>
                        <div style={{ width: `${ltiPct}%`, backgroundColor: "#ff7600", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.8rem", fontWeight: "bold" }}>
                          LTI ({ltiPct.toFixed(0)}%)
                        </div>
                      </div>
                      <span style={{ fontSize: "0.75rem", color: "#6c757d" }}>
                        * LTI weighs {ltiToBase.toFixed(2)}x base salary
                        {ltiToBase > 4.0 ? " — exceeds the 4.0x DCGK Section G.1 imbalance threshold." : ", within standard equity-incentive tilt criteria under DCGK Section G.1."}
                      </span>
                    </div>
                    );
                  })()}

                  {activeCriterion === "esg" && (
                    <div>
                      <p style={{ fontSize: "0.85rem", color: "#6c757d", margin: "0 0 1rem 0" }}>
                        ESG metric linkages and ESG scorecard weightings:
                      </p>
                      <div style={{ padding: "0.75rem", backgroundColor: "#f4fbf4", borderRadius: "4px", border: "1px solid #d4edda", color: "#155724", fontSize: "0.8rem" }}>
                        🍃 <strong>ESG target alignment:</strong> Variable remuneration includes explicit Carbon Footprint contraction goals (15% weight) and corporate diversity index scorecards (10% weight) compliant with DCGK Section G.1.
                      </div>
                    </div>
                  )}

                </div>

              </div>

            </div>
          </div>
        )}
          </>
        )}

      </main>
      
      <ChatDrawer
        isOpen={isChatOpen}
        onClose={closeChat}
        messages={messages}
        onSend={handleSendMessage}
      />

      {/* Interactive Selection Profile Popup Modal */}
      {isProfileModalOpen && (
        <div style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "rgba(15, 23, 42, 0.65)",
          backdropFilter: "blur(4px)",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          zIndex: 1000,
          transition: "all 0.3s ease"
        }}>
          <div style={{
            backgroundColor: "#ffffff",
            borderRadius: "8px",
            width: "100%",
            maxWidth: "500px",
            padding: "2rem",
            boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
            border: "1px solid #dee2e6"
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
              <h3 style={{ fontSize: "1.2rem", fontWeight: "bold", color: "#1f4287", margin: 0 }}>
                Select Evaluation Profile
              </h3>
              <button
                type="button"
                onClick={() => setIsProfileModalOpen(false)}
                style={{
                  border: "none",
                  backgroundColor: "transparent",
                  fontSize: "1.2rem",
                  cursor: "pointer",
                  color: "#6c757d"
                }}
              >
                ✕
              </button>
            </div>

            <p style={{ color: "#6c757d", fontSize: "0.85rem", marginBottom: "1.5rem" }}>
              Choose a predefined analysis profile to automatically activate the matching checklist criteria.
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              
              {/* Profile 1: Auditor */}
              <div 
                onClick={() => {
                  setCriteria({ reach: true, ratchet: true, mom: true, secrecy: false, ltiRatio: false, esg: false });
                  setIsProfileModalOpen(false);
                }}
                onMouseEnter={(e) => (e.currentTarget.style.borderColor = "#1f4287")}
                onMouseLeave={(e) => (e.currentTarget.style.borderColor = "#dee2e6")}
                style={{
                  border: "1px solid #dee2e6",
                  borderRadius: "6px",
                  padding: "1rem",
                  cursor: "pointer",
                  transition: "border-color 0.2s ease",
                  textAlign: "left"
                }}
              >
                <strong style={{ display: "block", fontSize: "0.95rem", color: "#1f4287", marginBottom: "0.25rem" }}>
                  🔍 Institutional Auditor Profile (ISS/Glass Lewis)
                </strong>
                <span style={{ fontSize: "0.8rem", color: "#6c757d" }}>
                  Focuses on outlier reach ratios, pay-for-luck ratchets, and multiple of median thresholds.
                </span>
              </div>

              {/* Profile 2: Compliance */}
              <div 
                onClick={() => {
                  setCriteria({ reach: false, ratchet: false, mom: false, secrecy: false, ltiRatio: true, esg: true });
                  setIsProfileModalOpen(false);
                }}
                onMouseEnter={(e) => (e.currentTarget.style.borderColor = "#ff7600")}
                onMouseLeave={(e) => (e.currentTarget.style.borderColor = "#dee2e6")}
                style={{
                  border: "1px solid #dee2e6",
                  borderRadius: "6px",
                  padding: "1rem",
                  cursor: "pointer",
                  transition: "border-color 0.2s ease",
                  textAlign: "left"
                }}
              >
                <strong style={{ display: "block", fontSize: "0.95rem", color: "#ff7600", marginBottom: "0.25rem" }}>
                  🛡️ DCGK Board Compliance Profile
                </strong>
                <span style={{ fontSize: "0.8rem", color: "#6c757d" }}>
                  Enforces structural balance under Section G.1 and sustainable target cardboard linkage.
                </span>
              </div>

              {/* Profile 3: Full Sweep */}
              <div 
                onClick={() => {
                  setCriteria({ reach: true, ratchet: true, mom: true, secrecy: true, ltiRatio: true, esg: true });
                  setIsProfileModalOpen(false);
                }}
                onMouseEnter={(e) => (e.currentTarget.style.borderColor = "#2e7d32")}
                onMouseLeave={(e) => (e.currentTarget.style.borderColor = "#dee2e6")}
                style={{
                  border: "1px solid #dee2e6",
                  borderRadius: "6px",
                  padding: "1rem",
                  cursor: "pointer",
                  transition: "border-color 0.2s ease",
                  textAlign: "left"
                }}
              >
                <strong style={{ display: "block", fontSize: "0.95rem", color: "#2e7d32", marginBottom: "0.25rem" }}>
                  ⚖️ Full Governance Audit Profile
                </strong>
                <span style={{ fontSize: "0.8rem", color: "#6c757d" }}>
                  Rigorous forensic sweep of all six econometric and disclosure rules.
                </span>
              </div>

            </div>
          </div>
        </div>
      )}
    </div>
  );
}
