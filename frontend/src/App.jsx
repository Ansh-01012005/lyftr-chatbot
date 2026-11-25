import { useState } from "react";

const API_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function newSessionId() {
  return globalThis.crypto?.randomUUID?.() || `s-${Date.now()}-${Math.random()}`;
}

export default function App() {
  const [sessionId] = useState(newSessionId);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [sending, setSending] = useState(false);

  async function sendMessage(event) {
    event.preventDefault();
    const message = input.trim();
    if (!message || sending) return;

    setInput("");
    setSending(true);
    setMessages((current) => [...current, { role: "user", content: message }]);

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          message,
          ...(systemPrompt.trim() ? { system_prompt: systemPrompt.trim() } : {}),
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        const detail = Array.isArray(data.detail)
          ? data.detail.map((item) => item.msg).join(", ")
          : data.detail;
        throw new Error(detail || "The request could not be completed.");
      }
      setMessages((current) => [
        ...current,
        { role: "assistant", content: data.reply, metadata: data.metadata },
      ]);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          role: "error",
          content: error.message || "Could not reach the chat service.",
        },
      ]);
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  return (
    <main className="app-shell">
      <section className="chat-card" aria-label="Lyftr AI chat">
        <header className="topbar">
          <div className="brand-mark" aria-hidden="true">L</div>
          <div>
            <p className="eyebrow">LYFTR AI</p>
            <h1>Chat workspace</h1>
          </div>
          <span className="session-pill">New session</span>
        </header>

        <div className="intro">
          <div className="sparkle" aria-hidden="true">✦</div>
          <p className="eyebrow">A little room to think</p>
          <h2>What can I help you with?</h2>
          <p>Ask a question, explore an idea, or pick up a conversation.</p>
        </div>

        <label className="system-prompt">
          <span>System prompt <small>optional</small></span>
          <input
            data-testid="system-prompt-input"
            value={systemPrompt}
            onChange={(event) => setSystemPrompt(event.target.value)}
            placeholder="For example: Keep answers brief"
            maxLength={4000}
          />
        </label>

        <section className="conversation" aria-live="polite">
          {messages.map((message, index) => {
            if (message.role === "user") {
              return (
                <div className="user-row" key={`user-${index}`}>
                  <div className="user-message">{message.content}</div>
                </div>
              );
            }
            if (message.role === "error") {
              return (
                <div className="error-message" role="alert" key={`error-${index}`}>
                  <span aria-hidden="true">!</span>
                  {message.content}
                </div>
              );
            }
            return (
              <article
                className="assistant-message"
                data-testid="assistant-message"
                key={`assistant-${index}`}
              >
                <div className="assistant-avatar" aria-hidden="true">L</div>
                <div className="assistant-content">
                  <p className="reply-text">{message.content}</p>
                  <div className="metadata">
                    <span className="source-tag" data-testid="meta-source">
                      {message.metadata.resolution_source}
                    </span>
                    <span data-testid="meta-model">{message.metadata.model}</span>
                    <span data-testid="meta-latency">
                      {message.metadata.latency_ms} ms
                    </span>
                    <span>
                      <span className="meta-label">In</span>{" "}
                      <span data-testid="meta-input-tokens">
                        {message.metadata.input_tokens}
                      </span>
                    </span>
                    <span>
                      <span className="meta-label">Out</span>{" "}
                      <span data-testid="meta-output-tokens">
                        {message.metadata.output_tokens}
                      </span>
                    </span>
                  </div>
                </div>
              </article>
            );
          })}
          {sending && <p className="typing-indicator">Thinking...</p>}
        </section>

        <form className="composer" onSubmit={sendMessage}>
          <textarea
            data-testid="chat-input"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Write a message..."
            aria-label="Write a message"
            rows={2}
            maxLength={4000}
          />
          <div className="composer-footer">
            <span>Enter to send, Shift + Enter for a new line</span>
            <button
              type="submit"
              data-testid="send-button"
              disabled={!input.trim() || sending}
            >
              {sending ? "Sending..." : "Send"}
              <span aria-hidden="true">↗</span>
            </button>
          </div>
        </form>
        <footer className="footnote">Responses can be imperfect. Check important details.</footer>
      </section>
    </main>
  );
}
