import type { ReactNode } from "react";
import { ArrowUpRight, CircleAlert, Feather } from "lucide-react";

type FigureCardProps = {
  number: string;
  eyebrow: string;
  title: string;
  deck: string;
  children: ReactNode;
  reading: string;
  limit: string;
  action?: string;
  onAction?: () => void;
  className?: string;
};

export function FigureCard({
  number,
  eyebrow,
  title,
  deck,
  children,
  reading,
  limit,
  action,
  onAction,
  className = "",
}: FigureCardProps) {
  return (
    <article className={`figure-card ${className}`}>
      <header className="figure-header">
        <div className="figure-number">{number}</div>
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h2>{title}</h2>
          <p className="figure-deck">{deck}</p>
        </div>
      </header>
      <div className="figure-stage">{children}</div>
      <footer className="figure-caption">
        <div className="caption-block">
          <Feather size={17} aria-hidden="true" />
          <p>
            <strong>Read this as</strong>
            {reading}
          </p>
        </div>
        <div className="caption-block caption-limit">
          <CircleAlert size={17} aria-hidden="true" />
          <p>
            <strong>Keep in mind</strong>
            {limit}
          </p>
        </div>
        {action && (
          <button className="text-action" type="button" onClick={onAction}>
            {action}
            <ArrowUpRight size={15} />
          </button>
        )}
      </footer>
    </article>
  );
}
