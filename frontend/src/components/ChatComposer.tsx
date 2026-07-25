import { Send, Square } from "lucide-react";
import { KeyboardEvent, useEffect, useRef, useState } from "react";

interface ChatComposerProps {
  onSend: (question: string) => void;
  onStop: () => void;
  isLoading: boolean;
}

const MAX_LENGTH = 2000;

export function ChatComposer({ onSend, onStop, isLoading }: ChatComposerProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
  }, [value]);

  const submit = () => {
    const question = value.trim();
    if (!question || isLoading) return;
    onSend(question);
    setValue("");
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <div className="composer-wrap">
      <div className="composer">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(event) => setValue(event.target.value.slice(0, MAX_LENGTH))}
          onKeyDown={handleKeyDown}
          placeholder="Ask about a national park…"
          rows={1}
          aria-label="Ask a question about national parks"
          disabled={isLoading}
        />
        {isLoading ? (
          <button className="composer__button composer__button--stop" type="button" onClick={onStop} aria-label="Stop response">
            <Square size={17} fill="currentColor" />
          </button>
        ) : (
          <button
            className="composer__button"
            type="button"
            onClick={submit}
            disabled={!value.trim()}
            aria-label="Send message"
          >
            <Send size={18} />
          </button>
        )}
      </div>
      <div className="composer-meta">
        <span>Enter to send · Shift + Enter for a new line</span>
        {value.length > 1600 && <span>{value.length}/{MAX_LENGTH}</span>}
      </div>
    </div>
  );
}
