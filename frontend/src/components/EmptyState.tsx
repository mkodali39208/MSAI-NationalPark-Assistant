import { Compass } from "lucide-react";
import { SuggestedPrompts } from "./SuggestedPrompts";

interface EmptyStateProps {
  onPrompt: (question: string) => void;
}

export function EmptyState({ onPrompt }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <span className="empty-state__icon" aria-hidden="true">
        <Compass size={31} />
      </span>
      <p className="eyebrow">Your park guide is ready</p>
      <h2>Where would you like to explore?</h2>
      <p className="empty-state__description">
        Ask about wildlife, trails, camping, safety, history, accessibility, or planning a visit.
      </p>
      <SuggestedPrompts onSelect={onPrompt} />
      <p className="empty-state__note">
        Answers are generated from the park information indexed by this project. Verify changing conditions with the National Park Service before travelling.
      </p>
    </div>
  );
}
