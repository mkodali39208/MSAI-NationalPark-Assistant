import { Binoculars, Footprints, MountainSnow, TentTree } from "lucide-react";

const prompts = [
  {
    icon: MountainSnow,
    title: "Plan a first visit",
    question: "What should a first-time visitor know about Yellowstone National Park?",
  },
  {
    icon: Footprints,
    title: "Find a hike",
    question: "Recommend beginner-friendly hikes in Yosemite National Park.",
  },
  {
    icon: Binoculars,
    title: "See wildlife",
    question: "What wildlife can I see in Great Smoky Mountains National Park?",
  },
  {
    icon: TentTree,
    title: "Prepare to camp",
    question: "What should I know before camping in Zion National Park?",
  },
];

interface SuggestedPromptsProps {
  onSelect: (question: string) => void;
  compact?: boolean;
}

export function SuggestedPrompts({ onSelect, compact = false }: SuggestedPromptsProps) {
  return (
    <div className={`prompt-grid ${compact ? "prompt-grid--compact" : ""}`}>
      {prompts.map(({ icon: Icon, title, question }) => (
        <button key={title} type="button" className="prompt-card" onClick={() => onSelect(question)}>
          <span className="prompt-card__icon">
            <Icon size={19} />
          </span>
          <span>
            <strong>{title}</strong>
            {!compact && <small>{question}</small>}
          </span>
        </button>
      ))}
    </div>
  );
}
