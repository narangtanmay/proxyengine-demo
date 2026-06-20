import { useRef } from "react";
import CompanyPicker from "./CompanyPicker";
import type { Company } from "../types";

interface HeaderProps {
  companies: Company[];
  selectedId: string;
  onCompanyChange: (id: string) => void;
  lens: string;
  onLensChange: (lens: string) => void;
  isChatOpen: boolean;
  onToggleChat: () => void;
  onPdfUploaded: (data: { trace: any; proposal: any }) => void;
}

export default function Header({ 
  companies, 
  selectedId, 
  onCompanyChange, 
  lens,
  onLensChange,
  isChatOpen, 
  onToggleChat,
  onPdfUploaded
}: HeaderProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("http://localhost:8000/api/upload-pdf", {
        method: "POST",
        body: formData,
      });
      if (!response.ok) throw new Error("Upload failed");
      const result = await response.json();
      onPdfUploaded(result);
      alert(`Successfully analyzed ${result.proposal.company_name}'s compensation report PDF!`);
    } catch (err) {
      console.error(err);
      alert("Error uploading PDF. Please ensure the backend is running at http://localhost:8000.");
    }
  };

  return (
    <header className="app-header">
      <h1 className="app-title" style={{ fontSize: "1.5rem", fontWeight: "bold" }}>
        ProxyEngine Say-on-Pay Strategic Terminal
      </h1>

      <div className="app-header__controls" style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
        <CompanyPicker 
          companies={companies} 
          selectedId={selectedId} 
          onCompanyChange={onCompanyChange} 
        />

        <div className="lens-toggle" style={{ display: "flex", gap: "4px", backgroundColor: "#f1f3f5", padding: "4px", borderRadius: "6px" }}>
          <button
            type="button"
            className="button"
            style={{ 
              padding: "6px 12px", 
              fontSize: "0.85rem",
              borderRadius: "4px",
              border: "none",
              cursor: "pointer",
              backgroundColor: lens === "auditor" ? "#1f4287" : "transparent",
              color: lens === "auditor" ? "#ffffff" : "#495057",
              fontWeight: lens === "auditor" ? "bold" : "normal"
            }}
            onClick={() => onLensChange("auditor")}
          >
            Auditor Mode
          </button>
          <button
            type="button"
            className="button"
            style={{ 
              padding: "6px 12px", 
              fontSize: "0.85rem",
              borderRadius: "4px",
              border: "none",
              cursor: "pointer",
              backgroundColor: lens === "compliance" ? "#ff7600" : "transparent",
              color: lens === "compliance" ? "#ffffff" : "#495057",
              fontWeight: lens === "compliance" ? "bold" : "normal"
            }}
            onClick={() => onLensChange("compliance")}
          >
            Compliance Mode
          </button>
        </div>

        <input 
          type="file" 
          ref={fileInputRef} 
          style={{ display: "none" }} 
          accept=".pdf" 
          onChange={handleFileChange}
        />
        
        <button
          type="button"
          className="button button--secondary"
          onClick={() => fileInputRef.current?.click()}
          style={{ border: "1px solid #ced4da", cursor: "pointer" }}
        >
          📂 Upload PDF
        </button>

        {!isChatOpen && (
          <button
            type="button"
            className="button button--primary"
            onClick={onToggleChat}
            aria-haspopup="dialog"
            aria-expanded={isChatOpen}
          >
            Ask AI Advisor
          </button>
        )}
      </div>
    </header>
  );
}
