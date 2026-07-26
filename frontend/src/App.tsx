import { BookOpenCheck, Database, ShieldCheck, Sparkles } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { BrandMark } from "./components/BrandMark";
import { ChatComposer } from "./components/ChatComposer";
import { ChatHeader } from "./components/ChatHeader";
import { ChatMessage } from "./components/ChatMessage";
import { EmptyState } from "./components/EmptyState";
import { SuggestedPrompts } from "./components/SuggestedPrompts";
import { useChat } from "./hooks/useChat";
import { checkHealth } from "./services/api";
import type { BackendStatus } from "./types/chat";

function App() {
  const { messages, isLoading, sendMessage, stopGeneration, clearMessages } = useChat();
  const [backendStatus, setBackendStatus] = useState<BackendStatus>("checking");
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const refreshHealth = useCallback(async () => {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 5000);

    try {
      await checkHealth(controller.signal);
      setBackendStatus("online");
    } catch {
      setBackendStatus("offline");
    } finally {
      window.clearTimeout(timeoutId);
    }
  }, []);

  useEffect(() => {
    void refreshHealth();
    const intervalId = window.setInterval(() => void refreshHealth(), 30000);
    return () => window.clearInterval(intervalId);
  }, [refreshHealth]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: isLoading ? "smooth" : "auto" });
  }, [messages, isLoading]);

  const handleSend = (question: string) => {
    void sendMessage(question);
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <BrandMark />

        <div className="sidebar__intro">
          <p className="eyebrow">RAG-powered guide</p>
          <h2>Explore with better context.</h2>
          <p>
            Ask natural follow-up questions while the assistant retrieves information from your indexed national park sources.
          </p>
        </div>

        <div className="sidebar__features">
          <div>
            <Database size={17} />
            <span>Qdrant vector retrieval</span>
          </div>
          <div>
            <Sparkles size={17} />
            <span>Groq answer generation</span>
          </div>
          <div>
            <BookOpenCheck size={17} />
            <span>Source-linked responses</span>
          </div>
          <div>
            <ShieldCheck size={17} />
            <span>API keys stay on backend</span>
          </div>
        </div>

        <div className="sidebar__prompts">
          <p className="sidebar__label">Quick questions</p>
          <SuggestedPrompts onSelect={handleSend} compact />
        </div>

        <p className="sidebar__footer">
          Built for educational use. Check current closures, weather, permits, and safety notices before visiting.
        </p>
      </aside>

      <main className="chat-panel">
        <ChatHeader
          status={backendStatus}
          hasMessages={messages.length > 0}
          onClear={clearMessages}
        />

        <section className="message-scroll" aria-live="polite">
          <div className="message-container">
            {messages.length === 0 ? (
              <EmptyState onPrompt={handleSend} />
            ) : (
              messages.map((message) => <ChatMessage key={message.id} message={message} />)
            )}
            <div ref={bottomRef} />
          </div>
        </section>

        {backendStatus === "offline" && (
          <div className="offline-banner" role="status">
            Backend unavailable. Start Uvicorn at <code>http://127.0.0.1:8000</code>, then refresh this page.
          </div>
        )}

        <ChatComposer onSend={handleSend} onStop={stopGeneration} isLoading={isLoading} />
      </main>
    </div>
  );
}

export default App;
