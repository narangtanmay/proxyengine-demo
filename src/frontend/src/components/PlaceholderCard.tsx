import type { ReactNode } from "react";

interface PlaceholderCardProps {
  title: string;
  children?: ReactNode;
}

/**
 * Generic, reusable bordered card with a title and a placeholder body.
 */
export default function PlaceholderCard({ title, children }: PlaceholderCardProps) {
  return (
    <article className="placeholder-card">
      <h2 className="placeholder-card__title">{title}</h2>
      <div className="placeholder-card__body">
        {children ?? <p className="placeholder-card__muted">Coming soon</p>}
      </div>
    </article>
  );
}
