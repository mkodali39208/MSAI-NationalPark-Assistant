interface BrandMarkProps {
  compact?: boolean;
}

export function BrandMark({ compact = false }: BrandMarkProps) {
  return (
    <div className={`brand ${compact ? "brand--compact" : ""}`} aria-label="Park Explorer AI">
      <span className="brand__icon" aria-hidden="true">
        <svg viewBox="0 0 64 64" role="img">
          <path d="M32 7 19 25h8L16 41h12v14h8V41h12L37 25h8L32 7Z" />
          <path d="M10 53h44" className="brand__ground" />
        </svg>
      </span>
      <span className="brand__copy">
        <strong>Park Explorer</strong>
        <small>National Parks AI</small>
      </span>
    </div>
  );
}
