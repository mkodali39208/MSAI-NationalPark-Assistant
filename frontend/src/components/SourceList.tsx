import { ExternalLink, MapPin } from "lucide-react";
import type { Source } from "../types/chat";

interface SourceListProps {
  sources: Source[];
}

function deduplicateSources(sources: Source[]): Source[] {
  const seen = new Set<string>();
  return sources.filter((source) => {
    const key = source.url || `${source.park_code}-${source.park_name}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function relevance(score: number): string | null {
  if (!Number.isFinite(score)) return null;
  const percentage = Math.max(0, Math.min(100, Math.round(score * 100)));
  return `${percentage}% match`;
}

export function SourceList({ sources }: SourceListProps) {
  const uniqueSources = deduplicateSources(sources).slice(0, 5);
  if (!uniqueSources.length) return null;

  return (
    <details className="sources">
      <summary>
        <span>Sources</span>
        <span className="sources__count">{uniqueSources.length}</span>
      </summary>
      <div className="sources__list">
        {uniqueSources.map((source, index) => {
          const score = relevance(source.score);
          const hasUrl = /^https?:\/\//i.test(source.url || "");

          const content = (
            <>
              <span className="sources__icon" aria-hidden="true">
                <MapPin size={16} />
              </span>
              <span className="sources__copy">
                <strong>{source.park_name || "National Park Service"}</strong>
                <small>
                  {source.park_code?.toUpperCase() || "NPS"}
                  {score ? ` · ${score}` : ""}
                </small>
              </span>
              {hasUrl && <ExternalLink size={15} className="sources__external" />}
            </>
          );

          return hasUrl ? (
            <a
              key={`${source.url}-${index}`}
              className="source-card"
              href={source.url}
              target="_blank"
              rel="noreferrer"
            >
              {content}
            </a>
          ) : (
            <div key={`${source.park_code}-${index}`} className="source-card">
              {content}
            </div>
          );
        })}
      </div>
    </details>
  );
}
