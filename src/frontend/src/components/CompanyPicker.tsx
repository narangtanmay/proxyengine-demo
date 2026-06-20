import { COMPANIES } from "../stubs";

/**
 * Static, non-functional company picker. Selecting an option has no effect yet.
 */
export default function CompanyPicker() {
  return (
    <label className="company-picker">
      <span className="visually-hidden">Select a company</span>
      {/* TODO: drive dashboard + chat context from selected company */}
      <select className="company-picker__select" defaultValue={COMPANIES[0]?.id}>
        {COMPANIES.map((company) => (
          <option key={company.id} value={company.id}>
            {company.name}
          </option>
        ))}
      </select>
    </label>
  );
}
