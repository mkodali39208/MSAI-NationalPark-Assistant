import type { BackendStatus } from "../types/chat";

interface StatusPillProps {
  status: BackendStatus;
}

const labels: Record<BackendStatus, string> = {
  checking: "Checking backend",
  online: "Backend online",
  offline: "Backend offline",
};

export function StatusPill({ status }: StatusPillProps) {
  return (
    <span className={`status-pill status-pill--${status}`} title={labels[status]}>
      <span className="status-pill__dot" />
      <span>{labels[status]}</span>
    </span>
  );
}
