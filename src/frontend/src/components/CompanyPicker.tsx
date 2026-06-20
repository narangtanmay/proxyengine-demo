import type { Company } from "../types";

interface CompanyPickerProps {
  companies: Company[];
  selectedId: string;
  onCompanyChange: (id: string) => void;
}

export default function CompanyPicker({ companies, selectedId, onCompanyChange }: CompanyPickerProps) {
  return (
    <label className="company-picker">
      <span className="visually-hidden">Select a company</span>
      <select 
        className="company-picker__select" 
        value={selectedId}
        onChange={(e) => onCompanyChange(e.target.value)}
      >
        {companies.map((company) => (
          <option key={company.id} value={company.id}>
            {company.name}
          </option>
        ))}
      </select>
    </label>
  );
}
