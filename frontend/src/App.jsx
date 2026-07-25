import { useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000/api/chat";

const suggestions = [
  "Tell me about Yellowstone National Park",
  "What are the best hikes in Zion National Park?",
  "What wildlife can I see in Yosemite National Park?",
  "What are the best viewpoints in Bryce Canyon?",
];

function App() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeParkCode, setActiveParkCode] = useState(null);

  const askQuestion = async (selectedQuestion) => {
    const finalQuestion =
      typeof selectedQuestion === "string" ? selectedQuestion : question;

    if (!finalQuestion.trim() || loading) {
      return;
    }

    const userMessage = {
      role: "user",
      content: finalQuestion.trim(),
    };

    const previousMessages = [...messages];

    setMessages((current) => [...current, userMessage]);
    setQuestion("");
    setLoading(true);

    try {
      const conversationHistory = previousMessages.map((message) => ({
        role: message.role,
        content: message.content,
      }));

      const response = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: finalQuestion.trim(),
          park_code: activeParkCode,
          top_k: 5,
          conversation_history:
            conversationHistory.length > 0 ? conversationHistory : null,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "The chatbot request failed.");
      }

      const assistantMessage = {
        role: "assistant",
        content: data.answer,
        sources: data.sources || [],
      };

      setMessages((current) => [...current, assistantMessage]);

      if (data.active_park_code) {
        setActiveParkCode(data.active_park_code);
      }
    } catch (error) {
      console.error("Chat request failed:", error);

      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content:
            "I could not connect to the chatbot backend. Make sure the FastAPI server is running on port 8000.",
          sources: [],
          isError: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const startNewChat = () => {
    setMessages([]);
    setQuestion("");
    setActiveParkCode(null);
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      askQuestion();
    }
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">🏔️</div>

          <div>
            <h2>National Parks</h2>
            <p>Explore. Ask. Discover.</p>
          </div>
        </div>

        <button className="new-chat-button" onClick={startNewChat}>
          <span>＋</span>
          New Chat
        </button>

        <nav className="sidebar-nav">
          <a href="#chat">
            <span>💬</span>
            Chat
          </a>

          <a href="#tips">
            <span>💡</span>
            Tips
          </a>

          <a href="#about">
            <span>ⓘ</span>
            About
          </a>
        </nav>

        <section className="tips-card" id="tips">
          <h3>Tips for better answers</h3>

          <p>
            <span>◎</span>
            Ask specific questions
          </p>

          <p>
            <span>△</span>
            Include the park name
          </p>

          <p>
            <span>☷</span>
            Ask about trails, wildlife, permits or facilities
          </p>
        </section>

        <div className="sidebar-landscape">
          <div className="sun" />
          <div className="mountain mountain-back" />
          <div className="mountain mountain-front" />
          <div className="tree tree-one">▲</div>
          <div className="tree tree-two">▲</div>
          <div className="tree tree-three">▲</div>
        </div>

        <footer className="sidebar-footer">
          <span>🌲</span>
          Data from National Park Service
        </footer>
      </aside>

      <main className="main-panel" id="chat">
        <header className="hero">
          <div className="hero-overlay" />

          <div className="hero-content">
            <div className="hero-icon">🌲</div>

            <div>
              <h1>National Parks Chatbot</h1>
              <p>Your guide to America’s natural treasures</p>
            </div>
          </div>
        </header>

        <section className="chat-area">
          {messages.length === 0 ? (
            <div className="welcome-state">
              <div className="welcome-icon">🏞️</div>

              <h2>Where would you like to explore?</h2>

              <p>
                Ask about trails, wildlife, camping, viewpoints, permits and
                visitor information.
              </p>

              <div className="suggestion-grid">
                {suggestions.map((suggestion) => (
                  <button
                    type="button"
                    className="suggestion-card"
                    key={suggestion}
                    onClick={() => askQuestion(suggestion)}
                  >
                    <span>↗</span>
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="messages">
              {messages.map((message, index) => (
                <article
                  className={`message-row ${message.role}`}
                  key={`${message.role}-${index}`}
                >
                  <div className="avatar">
                    {message.role === "user" ? "👤" : "🤖"}
                  </div>

                  <div className="message-content">
                    <div
                      className={`message-bubble ${
                        message.isError ? "error-message" : ""
                      }`}
                    >
                      {message.content}
                    </div>

                    {message.sources?.length > 0 && (
                      <div className="sources-card">
                        <h4>📖 Sources</h4>

                        <div className="source-list">
                          {message.sources.map((source, sourceIndex) => (
                            <a
                              href={source.url}
                              target="_blank"
                              rel="noreferrer"
                              key={`${source.url}-${sourceIndex}`}
                            >
                              <span>🔗</span>

                              <div>
                                <strong>
                                  {source.park_name || "National Park Service"}
                                </strong>
                                <small>{source.url}</small>
                              </div>
                            </a>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </article>
              ))}

              {loading && (
                <article className="message-row assistant">
                  <div className="avatar">🤖</div>

                  <div className="message-bubble loading-bubble">
                    <span />
                    <span />
                    <span />
                  </div>
                </article>
              )}
            </div>
          )}
        </section>

        <section className="composer-section">
          <div className="composer">
            <div className="composer-icon">🏔️</div>

            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything about a national park..."
              maxLength={1000}
              disabled={loading}
            />

            <button
              type="button"
              className="send-button"
              onClick={() => askQuestion()}
              disabled={loading || !question.trim()}
            >
              <span>➤</span>
              {loading ? "Thinking..." : "Send"}
            </button>
          </div>

          <div className="composer-meta">
            <span>{question.length} / 1000</span>
            <span>Press Enter to send · Shift + Enter for a new line</span>
          </div>
        </section>

        <footer className="main-footer" id="about">
          🛡️ This information is for general guidance. Verify current details
          on the official NPS website.
        </footer>
      </main>
    </div>
  );
}

export default App;