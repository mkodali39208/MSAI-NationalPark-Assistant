import { AlertTriangle, Bot, UserRound } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage as ChatMessageType } from "../types/chat";
import { SourceList } from "./SourceList";

interface ChatMessageProps {
  message: ChatMessageType;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";
  const isStreamingEmpty = message.state === "streaming" && !message.content;

  return (
    <article className={`message-row message-row--${message.role}`}>
      <div className={`message-avatar message-avatar--${message.role}`} aria-hidden="true">
        {isUser ? <UserRound size={18} /> : <Bot size={19} />}
      </div>
      <div className="message-column">
        <div className={`message-bubble message-bubble--${message.role} ${message.state === "error" ? "message-bubble--error" : ""}`}>
          {message.state === "error" && <AlertTriangle className="message-error-icon" size={18} />}
          {isStreamingEmpty ? (
            <span className="typing-indicator" aria-label="Generating answer">
              <span />
              <span />
              <span />
            </span>
          ) : isUser ? (
            <p>{message.content}</p>
          ) : (
            <div className="markdown-content">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  a: ({ children, ...props }) => (
                    <a {...props} target="_blank" rel="noreferrer">
                      {children}
                    </a>
                  ),
                }}
              >
                {message.content}
              </ReactMarkdown>
              {message.state === "streaming" && <span className="stream-cursor" aria-hidden="true" />}
            </div>
          )}
        </div>
        {!isUser && message.state === "complete" && message.sources && (
          <SourceList sources={message.sources} />
        )}
      </div>
    </article>
  );
}
