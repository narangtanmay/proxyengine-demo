import PlaceholderCard from "./PlaceholderCard";

const CARD_TITLES = [
  "Pay vs. peers",
  "Compensation breakdown",
  "Pay-for-performance",
  "Red flags",
  "Company overview",
] as const;

export default function Dashboard() {
  return (
    <section className="dashboard" aria-label="Compensation dashboard">
      {/* TODO: fetch GET /company/{id}/dashboard and render real content */}
      {/* TODO: render real charts here (e.g. Recharts) once data is available. */}
      <div className="dashboard__grid">
        {CARD_TITLES.map((title) => (
          <PlaceholderCard key={title} title={title}>
            <p className="placeholder-card__muted">No data yet</p>
          </PlaceholderCard>
        ))}
      </div>
    </section>
  );
}
