import { Trash2 } from "lucide-react";
import type { BackendStatus } from "../types/chat";
import { BrandMark } from "./BrandMark";
import { StatusPill } from "./StatusPill";

interface ChatHeaderProps {
  status: BackendStatus;
  hasMessages: boolean;
  onClear: () => void;
}

export function ChatHeader({ status, hasMessages, onClear }: ChatHeaderProps) {
  return (
    <header className="chat-header">
      <div className="chat-header__mobile-brand">
        <BrandMark compact />
      </div>
      <div className="chat-header__title">
        <h1>Ask about America&apos;s national parks</h1>
        <p>Official park information, conversationally explored.</p>
      </div>
      <div className="chat-header__actions">
        <StatusPill status={status} />
        <button
          className="icon-button"
          type="button"
          onClick={onClear}
          disabled={!hasMessages}
          title="Clear conversation"
          aria-label="Clear conversation"
        >
          <Trash2 size={18} />
        </button>
      </div>
    </header>
  );
}
