"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Link from "next/link";

type Source = {
  chunk_id: string;
  text: string;
  collection: string;
  score: number;
  metadata: Record<string, string | number>;
};

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  loading?: boolean;
};

const SUGGESTED = [
  "What are the water consumption metrics for FY2023?",
  "Which companies have the highest GHG emissions?",
  "Show ESG disclosures for Infosys in FY2023",
  "What are the key BRSR principle violations?",
];

function MarkdownMessage({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children }) => (
          <h1 style={{ margin: "0 0 10px", fontSize: 18, fontWeight: 600, color: "#e2e8f0" }}>{children}</h1>
        ),
        h2: ({ children }) => (
          <h2 style={{ margin: "0 0 9px", fontSize: 16, fontWeight: 600, color: "#e2e8f0" }}>{children}</h2>
        ),
        h3: ({ children }) => (
          <h3 style={{ margin: "0 0 8px", fontSize: 14, fontWeight: 600, color: "#e2e8f0" }}>{children}</h3>
        ),
        p: ({ children }) => (
          <p style={{ margin: "0 0 10px", color: "#cbd5e1" }}>{children}</p>
        ),
        ul: ({ children }) => (
          <ul style={{ margin: "0 0 10px", paddingLeft: 20, color: "#cbd5e1" }}>{children}</ul>
        ),
        ol: ({ children }) => (
          <ol style={{ margin: "0 0 10px", paddingLeft: 20, color: "#cbd5e1" }}>{children}</ol>
        ),
        li: ({ children }) => (
          <li style={{ marginBottom: 4 }}>{children}</li>
        ),
        strong: ({ children }) => (
          <strong style={{ color: "#f8fafc", fontWeight: 600 }}>{children}</strong>
        ),
        em: ({ children }) => (
          <em style={{ color: "#e2e8f0" }}>{children}</em>
        ),
        code: ({ children }) => (
          <code style={{ background: "#0a0a0f", border: "1px solid #1e2030", borderRadius: 4, padding: "1px 5px", fontSize: "0.92em", color: "#c4b5fd" }}>
            {children}
          </code>
        ),
        blockquote: ({ children }) => (
          <blockquote style={{ margin: "0 0 10px", paddingLeft: 12, borderLeft: "2px solid #334155", color: "#94a3b8" }}>
            {children}
          </blockquote>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

export default function ResearchPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [activeSource, setActiveSource] = useState<Message | null>(null);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (query: string) => {
    if (!query.trim() || loading) return;
    setInput("");
    setActiveSource(null);

    const userMsg: Message = { id: crypto.randomUUID(), role: "user", content: query };
    const loadingMsg: Message = { id: crypto.randomUUID(), role: "assistant", content: "", loading: true };
    setMessages((prev) => [...prev, userMsg, loadingMsg]);
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, top_k: 5 }),
      });
      const data = await res.json();

      const assistantMsg: Message = {
        id: loadingMsg.id,
        role: "assistant",
        content: data.answer,
        sources: data.sources,
      };
      setMessages((prev) => prev.map((m) => (m.id === loadingMsg.id ? assistantMsg : m)));
      setActiveSource(assistantMsg);
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === loadingMsg.id
            ? { ...m, loading: false, content: "Failed to reach the backend. Is it running on port 8000?" }
            : m
        )
      );
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  };

  const scoreColor = (score: number) => {
    if (score >= 0.85) return "#22c55e";
    if (score >= 0.7) return "#f59e0b";
    return "#94a3b8";
  };

  const collectionLabel = (col: string) =>
    col.toLowerCase().includes("narrative") ? "Narrative" : "Numeric";

  return (
    <div style={{ display: "flex", height: "100vh", background: "#0a0a0f", color: "#e2e8f0", fontFamily: "var(--font-sans, DM Sans, sans-serif)", overflow: "hidden" }}>

      {/* ── Left sidebar: branding ── */}
      <aside style={{ width: 220, borderRight: "1px solid #1e2030", display: "flex", flexDirection: "column", padding: "28px 20px", flexShrink: 0 }}>
        <div style={{ marginBottom: 32 }}>
          <Link href="/" style={{ textDecoration: "none" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6, cursor: "pointer" }}>
              <div style={{ width: 28, height: 28, borderRadius: 6, background: "linear-gradient(135deg,#6366f1,#22d3ee)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 12L6 4l4 6 2-3 2 5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
              </div>
              <span style={{ fontSize: 14, fontWeight: 500, letterSpacing: "-0.01em", color: "#e2e8f0" }}>BRSR Analyst</span>
            </div>
          </Link>
          <p style={{ fontSize: 11, color: "#475569", margin: 0, lineHeight: 1.5 }}>ESG Intelligence<br />for Investors</p>
        </div>

        <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.1em", color: "#334155", marginBottom: 10 }}>Collections</div>
        {["narrativecollection", "numericalcollection"].map((c) => (
          <div key={c} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0" }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#22c55e", flexShrink: 0 }} />
            <span style={{ fontSize: 12, color: "#64748b" }}>{collectionLabel(c)}</span>
          </div>
        ))}

        <div style={{ marginTop: "auto" }}>
          <Link href="/" style={{ display: "flex", alignItems: "center", gap: 6, textDecoration: "none", color: "#475569", fontSize: 12, marginBottom: 16, padding: "6px 0" }}>
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
            Back to Dashboard
          </Link>
          <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.1em", color: "#334155", marginBottom: 10 }}>Model</div>
          <div style={{ fontSize: 11, color: "#475569", lineHeight: 1.6 }}>
            gemini-2.5-flash-lite<br />
            all-MiniLM-L6-v2
          </div>
        </div>
      </aside>

      {/* ── Main chat ── */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* Header */}
        <header style={{ borderBottom: "1px solid #1e2030", padding: "16px 28px", display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
          <div>
            <h1 style={{ margin: 0, fontSize: 15, fontWeight: 500, letterSpacing: "-0.01em" }}>BRSR Research Assistant</h1>
            <p style={{ margin: 0, fontSize: 12, color: "#475569" }}>Ask about ESG metrics, sustainability disclosures, and principle compliance</p>
          </div>
          {messages.length > 0 && (
            <button
              onClick={() => { setMessages([]); setActiveSource(null); }}
              style={{ fontSize: 12, color: "#475569", background: "none", border: "1px solid #1e2030", borderRadius: 6, padding: "5px 12px", cursor: "pointer" }}
            >
              Clear chat
            </button>
          )}
        </header>

        {/* Messages */}
        <div style={{ flex: 1, overflowY: "auto", padding: "24px 28px", display: "flex", flexDirection: "column", gap: 20 }}>
          {messages.length === 0 && (
            <div style={{ margin: "auto", maxWidth: 520, textAlign: "center" }}>
              <div style={{ fontSize: 36, marginBottom: 12, opacity: 0.15 }}>
                <svg width="48" height="48" viewBox="0 0 48 48" fill="none" style={{ display: "inline-block" }}>
                  <rect width="48" height="48" rx="12" fill="#6366f1" fillOpacity="0.15" />
                  <path d="M10 32L18 12l12 18 6-9 6 15" stroke="#6366f1" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <h2 style={{ fontSize: 20, fontWeight: 400, color: "#94a3b8", margin: "0 0 6px", letterSpacing: "-0.02em" }}>
                What would you like to analyse?
              </h2>
              <p style={{ fontSize: 13, color: "#334155", margin: "0 0 28px" }}>
                Query BRSR disclosures across narrative and numeric data
              </p>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                {SUGGESTED.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    style={{ textAlign: "left", padding: "10px 14px", background: "#0f1117", border: "1px solid #1e2030", borderRadius: 8, cursor: "pointer", fontSize: 12, color: "#64748b", lineHeight: 1.5, transition: "border-color 0.15s", fontFamily: "inherit" }}
                    onMouseEnter={(e) => (e.currentTarget.style.borderColor = "#6366f1")}
                    onMouseLeave={(e) => (e.currentTarget.style.borderColor = "#1e2030")}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} style={{ display: "flex", gap: 12, alignItems: "flex-start", flexDirection: msg.role === "user" ? "row-reverse" : "row" }}>
              <div style={{ width: 28, height: 28, borderRadius: 6, background: msg.role === "user" ? "#1e293b" : "linear-gradient(135deg,#6366f1,#22d3ee)", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", marginTop: 2 }}>
                {msg.role === "user"
                  ? <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="5" r="3" stroke="#94a3b8" strokeWidth="1.5" /><path d="M2 14c0-3.3 2.7-6 6-6s6 2.7 6 6" stroke="#94a3b8" strokeWidth="1.5" strokeLinecap="round" /></svg>
                  : <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M2 10L5 3l5 7 3-4.5L16 10" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
                }
              </div>

              <div style={{ maxWidth: "78%", display: "flex", flexDirection: "column", gap: 6, alignItems: msg.role === "user" ? "flex-end" : "flex-start" }}>
                <div style={{ background: msg.role === "user" ? "#1e293b" : "#0f1117", border: `1px solid ${msg.role === "user" ? "#2d3748" : "#1e2030"}`, borderRadius: msg.role === "user" ? "12px 12px 2px 12px" : "12px 12px 12px 2px", padding: "12px 16px", fontSize: 13.5, lineHeight: 1.7, color: msg.loading ? "#475569" : "#cbd5e1" }}>
                  {msg.loading ? (
                    <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                      {[0, 1, 2].map((i) => (
                        <div key={i} style={{ width: 5, height: 5, borderRadius: "50%", background: "#6366f1", animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite` }} />
                      ))}
                    </div>
                  ) : msg.role === "assistant" ? (
                    <MarkdownMessage content={msg.content} />
                  ) : (
                    msg.content
                  )}
                </div>

                {msg.sources && msg.sources.length > 0 && (
                  <button
                    onClick={() => setActiveSource(activeSource?.id === msg.id ? null : msg)}
                    style={{ fontSize: 11, color: "#6366f1", background: "none", border: "1px solid #312e81", borderRadius: 6, padding: "3px 10px", cursor: "pointer", fontFamily: "inherit" }}
                  >
                    {activeSource?.id === msg.id ? "Hide" : "View"} {msg.sources.length} sources
                  </button>
                )}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div style={{ borderTop: "1px solid #1e2030", padding: "16px 28px", flexShrink: 0 }}>
          <div style={{ display: "flex", gap: 10, alignItems: "flex-end", background: "#0f1117", border: "1px solid #1e2030", borderRadius: 10, padding: "10px 14px" }}>
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask about ESG metrics, BRSR disclosures, company sustainability data…"
              rows={1}
              style={{ flex: 1, background: "none", border: "none", outline: "none", resize: "none", fontSize: 13.5, color: "#e2e8f0", lineHeight: 1.6, fontFamily: "inherit", maxHeight: 120 }}
            />
            <button
              onClick={() => send(input)}
              disabled={!input.trim() || loading}
              style={{ width: 32, height: 32, borderRadius: 7, background: input.trim() && !loading ? "#6366f1" : "#1e2030", border: "none", cursor: input.trim() && !loading ? "pointer" : "default", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, transition: "background 0.15s" }}
            >
              <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M2 8h12M9 3l5 5-5 5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
            </button>
          </div>
          <p style={{ fontSize: 11, color: "#1e293b", margin: "8px 0 0", textAlign: "center" }}>
            Enter to send · Shift+Enter for new line
          </p>
        </div>
      </main>

      {/* ── Right panel: sources ── */}
      <aside style={{ width: activeSource ? 340 : 0, borderLeft: activeSource ? "1px solid #1e2030" : "none", overflow: "hidden", transition: "width 0.25s ease", flexShrink: 0, display: "flex", flexDirection: "column" }}>
        {activeSource && (
          <>
            <div style={{ padding: "16px 20px", borderBottom: "1px solid #1e2030", display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 500 }}>Source Chunks</div>
                <div style={{ fontSize: 11, color: "#475569" }}>{activeSource.sources?.length} retrieved</div>
              </div>
              <button onClick={() => setActiveSource(null)} style={{ background: "none", border: "none", cursor: "pointer", color: "#475569", padding: 4 }}>
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
              </button>
            </div>

            <div style={{ flex: 1, overflowY: "auto", padding: "16px 16px" }}>
              {activeSource.sources?.map((src, i) => (
                <div key={src.chunk_id} style={{ marginBottom: 12, background: "#0f1117", border: "1px solid #1e2030", borderRadius: 8, overflow: "hidden" }}>
                  <div style={{ padding: "10px 14px", borderBottom: "1px solid #1e2030", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <span style={{ fontSize: 10, background: src.collection.includes("narrative") ? "#1e1b4b" : "#052e16", color: src.collection.includes("narrative") ? "#818cf8" : "#4ade80", padding: "2px 7px", borderRadius: 4, fontFamily: "var(--font-mono)", letterSpacing: "0.02em" }}>
                        {collectionLabel(src.collection)}
                      </span>
                      <span style={{ fontSize: 10, color: "#334155" }}>#{i + 1}</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <div style={{ width: 6, height: 6, borderRadius: "50%", background: scoreColor(src.score) }} />
                      <span style={{ fontSize: 10, color: "#475569", fontFamily: "var(--font-mono)" }}>{(src.score * 100).toFixed(0)}%</span>
                    </div>
                  </div>

                  <div style={{ padding: "8px 14px", display: "flex", flexWrap: "wrap", gap: 4, borderBottom: "1px solid #1e2030" }}>
                    {Object.entries(src.metadata)
                      .filter(([k, v]) => v && !["strategy", "source_file", "row_count"].includes(k))
                      .slice(0, 5)
                      .map(([k, v]) => (
                        <span key={k} style={{ fontSize: 10, background: "#0a0a0f", border: "1px solid #1e2030", borderRadius: 4, padding: "2px 7px", color: "#475569" }}>
                          <span style={{ color: "#334155" }}>{k}:</span> {String(v)}
                        </span>
                      ))}
                  </div>

                  <div style={{ padding: "10px 14px", fontSize: 11.5, color: "#475569", lineHeight: 1.65, maxHeight: 140, overflowY: "auto", fontFamily: src.collection.includes("numerical") ? "var(--font-mono)" : "inherit" }}>
                    {src.text.length > 400 ? src.text.slice(0, 400) + "…" : src.text}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </aside>

      <style>{`
        * { box-sizing: border-box; }
        body { margin: 0; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #1e2030; border-radius: 2px; }
        @keyframes pulse {
          0%, 100% { opacity: 0.3; transform: scale(0.8); }
          50% { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </div>
  );
}