"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Link from "next/link";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

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

type SectionResult = {
  title: string;
  chunk_count: number;
  sources: Source[];
};

type DueDiligenceResult = {
  company: string;
  symbol: string | null;
  report_markdown: string;
  sections: SectionResult[];
  total_sources: number;
};

type ActiveSources = {
  label: string;
  sources: Source[];
};

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const SUGGESTED = [
  "What are the water consumption metrics for FY2023?",
  "Which companies have the highest GHG emissions?",
  "Show ESG disclosures for Infosys in FY2023",
  "What are the key BRSR principle violations?",
];

const DD_SECTIONS = [
  "Company Profile & Operations",
  "Financial Overview",
  "Workforce & Diversity",
  "Health, Safety & Training",
  "Environmental — GHG & Energy",
  "Environmental — Water & Waste",
  "Governance & Ethics",
  "Consumer Responsibility",
  "Stakeholder Engagement & CSR",
  "Policy & Sustainability Disclosures",
];

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function MarkdownMessage({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children }) => (
          <h1 style={{ margin: "0 0 12px", fontSize: 24, fontWeight: 600, color: "#e2e8f0" }}>{children}</h1>
        ),
        h2: ({ children }) => (
          <h2 style={{ margin: "18px 0 10px", fontSize: 20, fontWeight: 600, color: "#e2e8f0" }}>{children}</h2>
        ),
        h3: ({ children }) => (
          <h3 style={{ margin: "14px 0 8px", fontSize: 17, fontWeight: 600, color: "#e2e8f0" }}>{children}</h3>
        ),
        p: ({ children }) => (
          <p style={{ margin: "0 0 12px", fontSize: 15, color: "#cbd5e1" }}>{children}</p>
        ),
        ul: ({ children }) => (
          <ul style={{ margin: "0 0 12px", paddingLeft: 22, color: "#cbd5e1", fontSize: 15 }}>{children}</ul>
        ),
        ol: ({ children }) => (
          <ol style={{ margin: "0 0 12px", paddingLeft: 22, color: "#cbd5e1", fontSize: 15 }}>{children}</ol>
        ),
        li: ({ children }) => (
          <li style={{ marginBottom: 5 }}>{children}</li>
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
        table: ({ children }) => (
          <div style={{ overflowX: "auto", marginBottom: 14 }}>
            <table style={{ borderCollapse: "collapse", fontSize: 14, color: "#cbd5e1", width: "100%" }}>
              {children}
            </table>
          </div>
        ),
        th: ({ children }) => (
          <th style={{ padding: "8px 14px", borderBottom: "1px solid #1e2030", textAlign: "left", color: "#94a3b8", fontWeight: 600, background: "#0f1117" }}>{children}</th>
        ),
        td: ({ children }) => (
          <td style={{ padding: "8px 14px", borderBottom: "1px solid #0f1117", verticalAlign: "top" }}>{children}</td>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ResearchPage() {
  // Chat mode state
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);

  // Due Diligence mode state
  const [ddCompany, setDdCompany] = useState("");
  const [ddSymbol, setDdSymbol] = useState("");
  const [ddReport, setDdReport] = useState<DueDiligenceResult | null>(null);
  const [ddLoading, setDdLoading] = useState(false);
  const [ddSectionIdx, setDdSectionIdx] = useState(0);

  // Shared state
  const [mode, setMode] = useState<"chat" | "due-diligence">("chat");
  const [activeSources, setActiveSources] = useState<ActiveSources | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const ddInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Cycle through section names while loading
  useEffect(() => {
    if (!ddLoading) return;
    const id = setInterval(() => {
      setDdSectionIdx((i) => (i + 1) % DD_SECTIONS.length);
    }, 1800);
    return () => clearInterval(id);
  }, [ddLoading]);

  // ---------------------------------------------------------------------------
  // Chat handlers
  // ---------------------------------------------------------------------------

  const send = async (query: string) => {
    if (!query.trim() || chatLoading) return;
    setInput("");
    setActiveSources(null);

    const userMsg: Message = { id: crypto.randomUUID(), role: "user", content: query };
    const loadingMsg: Message = { id: crypto.randomUUID(), role: "assistant", content: "", loading: true };
    setMessages((prev) => [...prev, userMsg, loadingMsg]);
    setChatLoading(true);

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
      setActiveSources({ label: `${data.sources?.length ?? 0} sources`, sources: data.sources ?? [] });
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === loadingMsg.id
            ? { ...m, loading: false, content: "Failed to reach the backend. Is it running on port 8000?" }
            : m
        )
      );
    } finally {
      setChatLoading(false);
    }
  };

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  };

  // ---------------------------------------------------------------------------
  // Due Diligence handler
  // ---------------------------------------------------------------------------

  const generateReport = useCallback(async () => {
    if (!ddCompany.trim() || ddLoading) return;
    setDdReport(null);
    setActiveSources(null);
    setDdSectionIdx(0);
    setDdLoading(true);

    try {
      const res = await fetch("http://localhost:8000/due-diligence", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company: ddCompany.trim(),
          symbol: ddSymbol.trim() || undefined,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `HTTP ${res.status}`);
      }

      const data: DueDiligenceResult = await res.json();
      setDdReport(data);

      // Collect all sources across sections for the panel
      const allSources: Source[] = [];
      const seen = new Set<string>();
      for (const sec of data.sections) {
        for (const src of sec.sources) {
          if (!seen.has(src.chunk_id)) {
            seen.add(src.chunk_id);
            allSources.push(src);
          }
        }
      }
      setActiveSources({ label: `${data.total_sources} sources`, sources: allSources });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setDdReport({
        company: ddCompany,
        symbol: ddSymbol || null,
        report_markdown: `**Error generating report:** ${message}\n\nPlease ensure the backend is running and Weaviate is accessible.`,
        sections: [],
        total_sources: 0,
      });
    } finally {
      setDdLoading(false);
    }
  }, [ddCompany, ddSymbol, ddLoading]);

  const handleDdKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") generateReport();
  };

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  const scoreColor = (score: number) => {
    if (score >= 0.85) return "#22c55e";
    if (score >= 0.7) return "#f59e0b";
    return "#94a3b8";
  };

  const collectionLabel = (col: string) =>
    col.toLowerCase().includes("narrative") ? "Narrative" : "Numeric";

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div style={{ display: "flex", height: "100vh", background: "#0a0a0f", color: "#e2e8f0", fontFamily: "var(--font-sans, DM Sans, sans-serif)", overflow: "hidden" }}>

      {/* ── Left sidebar ── */}
      <aside style={{ width: 220, borderRight: "1px solid #1e2030", display: "flex", flexDirection: "column", padding: "28px 20px", flexShrink: 0 }}>
        <div style={{ marginBottom: 32 }}>
          <Link href="/" style={{ textDecoration: "none" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6, cursor: "pointer" }}>
              <div style={{ width: 28, height: 28, borderRadius: 6, background: "linear-gradient(135deg,#6366f1,#22d3ee)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 12L6 4l4 6 2-3 2 5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
              </div>
              <span style={{ fontSize: 15, fontWeight: 500, letterSpacing: "-0.01em", color: "#e2e8f0" }}>BRSR Analyst</span>
            </div>
          </Link>
          <p style={{ fontSize: 12, color: "#475569", margin: 0, lineHeight: 1.5 }}>ESG Intelligence<br />for Investors</p>
        </div>

        <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.1em", color: "#334155", marginBottom: 10 }}>Collections</div>
        {["narrativecollection", "numericalcollection"].map((c) => (
          <div key={c} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0" }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#22c55e", flexShrink: 0 }} />
            <span style={{ fontSize: 13, color: "#64748b" }}>{collectionLabel(c)}</span>
          </div>
        ))}

        <div style={{ marginTop: "auto" }}>
          <Link href="/" style={{ display: "flex", alignItems: "center", gap: 6, textDecoration: "none", color: "#475569", fontSize: 13, marginBottom: 16, padding: "6px 0" }}>
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
            Back to Dashboard
          </Link>
          <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.1em", color: "#334155", marginBottom: 10 }}>Model</div>
          <div style={{ fontSize: 12, color: "#475569", lineHeight: 1.6 }}>
            llama-3.1-8b-instant<br />
            all-MiniLM-L6-v2
          </div>
        </div>
      </aside>

      {/* ── Main area ── */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

        {/* Header with mode toggle */}
        <header style={{ borderBottom: "1px solid #1e2030", padding: "14px 28px", display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
            <div>
              <h1 style={{ margin: 0, fontSize: 17, fontWeight: 500, letterSpacing: "-0.01em" }}>BRSR Research Assistant</h1>
              <p style={{ margin: 0, fontSize: 13, color: "#475569" }}>
                {mode === "chat" ? "Ask about ESG metrics, sustainability disclosures, and principle compliance" : "Generate a structured due diligence report from BRSR data"}
              </p>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {/* Mode toggle */}
            <div style={{ display: "flex", background: "#0f1117", border: "1px solid #1e2030", borderRadius: 8, overflow: "hidden", padding: 3, gap: 2 }}>
              {(["chat", "due-diligence"] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => { setMode(m); setActiveSources(null); }}
                  style={{
                  padding: "6px 16px",
                  fontSize: 14,
                  fontWeight: mode === m ? 500 : 400,
                    background: mode === m ? "#1e2030" : "transparent",
                    color: mode === m ? "#e2e8f0" : "#475569",
                    border: "none",
                    borderRadius: 6,
                    cursor: "pointer",
                    fontFamily: "inherit",
                    transition: "all 0.15s",
                    whiteSpace: "nowrap",
                  }}
                >
                  {m === "chat" ? "Chat" : "Due Diligence"}
                </button>
              ))}
            </div>

            {mode === "chat" && messages.length > 0 && (
              <button
                onClick={() => { setMessages([]); setActiveSources(null); }}
                style={{ fontSize: 13, color: "#475569", background: "none", border: "1px solid #1e2030", borderRadius: 6, padding: "6px 14px", cursor: "pointer" }}
              >
                Clear chat
              </button>
            )}

            {mode === "due-diligence" && ddReport && (
              <button
                onClick={() => { setDdReport(null); setActiveSources(null); setDdCompany(""); setDdSymbol(""); }}
                style={{ fontSize: 13, color: "#475569", background: "none", border: "1px solid #1e2030", borderRadius: 6, padding: "6px 14px", cursor: "pointer" }}
              >
                New report
              </button>
            )}
          </div>
        </header>

        {/* ── CHAT MODE ── */}
        {mode === "chat" && (
          <>
            <div style={{ flex: 1, overflowY: "auto", padding: "24px 28px", display: "flex", flexDirection: "column", gap: 20 }}>
              {messages.length === 0 && (
                <div style={{ margin: "auto", maxWidth: 520, textAlign: "center" }}>
                  <div style={{ fontSize: 36, marginBottom: 12, opacity: 0.15 }}>
                    <svg width="48" height="48" viewBox="0 0 48 48" fill="none" style={{ display: "inline-block" }}>
                      <rect width="48" height="48" rx="12" fill="#6366f1" fillOpacity="0.15" />
                      <path d="M10 32L18 12l12 18 6-9 6 15" stroke="#6366f1" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </div>
                  <h2 style={{ fontSize: 22, fontWeight: 400, color: "#94a3b8", margin: "0 0 8px", letterSpacing: "-0.02em" }}>
                    What would you like to analyse?
                  </h2>
                  <p style={{ fontSize: 15, color: "#334155", margin: "0 0 28px" }}>
                    Query BRSR disclosures across narrative and numeric data
                  </p>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                    {SUGGESTED.map((s) => (
                      <button
                        key={s}
                        onClick={() => send(s)}
                        style={{ textAlign: "left", padding: "12px 16px", background: "#0f1117", border: "1px solid #1e2030", borderRadius: 8, cursor: "pointer", fontSize: 14, color: "#64748b", lineHeight: 1.5, transition: "border-color 0.15s", fontFamily: "inherit" }}
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
                    <div style={{ background: msg.role === "user" ? "#1e293b" : "#0f1117", border: `1px solid ${msg.role === "user" ? "#2d3748" : "#1e2030"}`, borderRadius: msg.role === "user" ? "12px 12px 2px 12px" : "12px 12px 12px 2px", padding: "14px 18px", fontSize: 15, lineHeight: 1.75, color: msg.loading ? "#475569" : "#cbd5e1" }}>
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
                        onClick={() => {
                          const current = activeSources?.sources === msg.sources;
                          setActiveSources(current ? null : { label: `${msg.sources!.length} sources`, sources: msg.sources! });
                        }}
                        style={{ fontSize: 13, color: "#6366f1", background: "none", border: "1px solid #312e81", borderRadius: 6, padding: "4px 12px", cursor: "pointer", fontFamily: "inherit" }}
                      >
                        {activeSources?.sources === msg.sources ? "Hide" : "View"} {msg.sources.length} sources
                      </button>
                    )}
                  </div>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>

            <div style={{ borderTop: "1px solid #1e2030", padding: "16px 28px", flexShrink: 0 }}>
              <div style={{ display: "flex", gap: 10, alignItems: "flex-end", background: "#0f1117", border: "1px solid #1e2030", borderRadius: 10, padding: "10px 14px" }}>
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKey}
                  placeholder="Ask about ESG metrics, BRSR disclosures, company sustainability data…"
                  rows={1}
                  style={{ flex: 1, background: "none", border: "none", outline: "none", resize: "none", fontSize: 15, color: "#e2e8f0", lineHeight: 1.6, fontFamily: "inherit", maxHeight: 120 }}
                />
                <button
                  onClick={() => send(input)}
                  disabled={!input.trim() || chatLoading}
                  style={{ width: 32, height: 32, borderRadius: 7, background: input.trim() && !chatLoading ? "#6366f1" : "#1e2030", border: "none", cursor: input.trim() && !chatLoading ? "pointer" : "default", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, transition: "background 0.15s" }}
                >
                  <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M2 8h12M9 3l5 5-5 5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
                </button>
              </div>
              <p style={{ fontSize: 12, color: "#1e293b", margin: "8px 0 0", textAlign: "center" }}>
                Enter to send · Shift+Enter for new line
              </p>
            </div>
          </>
        )}

        {/* ── DUE DILIGENCE MODE ── */}
        {mode === "due-diligence" && (
          <div style={{ flex: 1, overflowY: "auto", padding: "32px 40px", display: "flex", flexDirection: "column", gap: 24 }}>

            {/* Input card — always visible when no report yet */}
            {!ddReport && !ddLoading && (
              <div style={{ maxWidth: 600, margin: "auto", width: "100%", textAlign: "center" }}>
                <div style={{ marginBottom: 24, opacity: 0.2 }}>
                  <svg width="52" height="52" viewBox="0 0 52 52" fill="none" style={{ display: "inline-block" }}>
                    <rect width="52" height="52" rx="14" fill="#6366f1" fillOpacity="0.2" />
                    <path d="M14 36L20 18l10 16 6-9 8 11" stroke="#6366f1" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                    <circle cx="38" cy="16" r="4" stroke="#22d3ee" strokeWidth="2" />
                  </svg>
                </div>
                <h2 style={{ fontSize: 26, fontWeight: 400, color: "#94a3b8", margin: "0 0 10px", letterSpacing: "-0.02em" }}>
                  Due Diligence Report
                </h2>
                <p style={{ fontSize: 15, color: "#334155", margin: "0 0 32px", lineHeight: 1.7 }}>
                  Enter a company name or NSE ticker. The agent will query 10 BRSR sections<br />
                  and generate a structured report sourced exclusively from the indexed data.
                </p>

                <div style={{ background: "#0f1117", border: "1px solid #1e2030", borderRadius: 12, padding: 24, textAlign: "left" }}>
                  <label style={{ fontSize: 12, color: "#475569", textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: 8 }}>
                    Company name or symbol
                  </label>
                  <input
                    ref={ddInputRef}
                    value={ddCompany}
                    onChange={(e) => setDdCompany(e.target.value)}
                    onKeyDown={handleDdKey}
                    placeholder="e.g. Infosys or INFY"
                    style={{ width: "100%", background: "#0a0a0f", border: "1px solid #1e2030", borderRadius: 8, padding: "12px 16px", fontSize: 15, color: "#e2e8f0", outline: "none", fontFamily: "inherit", boxSizing: "border-box", marginBottom: 14 }}
                  />

                  <label style={{ fontSize: 12, color: "#475569", textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: 8 }}>
                    NSE ticker (optional — narrows to exact symbol)
                  </label>
                  <input
                    value={ddSymbol}
                    onChange={(e) => setDdSymbol(e.target.value)}
                    onKeyDown={handleDdKey}
                    placeholder="e.g. INFY"
                    style={{ width: "100%", background: "#0a0a0f", border: "1px solid #1e2030", borderRadius: 8, padding: "12px 16px", fontSize: 15, color: "#e2e8f0", outline: "none", fontFamily: "inherit", boxSizing: "border-box", marginBottom: 22 }}
                  />

                  <button
                    onClick={generateReport}
                    disabled={!ddCompany.trim()}
                    style={{
                      width: "100%",
                      padding: "13px 0",
                      background: ddCompany.trim() ? "linear-gradient(135deg,#6366f1,#4f46e5)" : "#1e2030",
                      border: "none",
                      borderRadius: 8,
                      color: ddCompany.trim() ? "#fff" : "#334155",
                      fontSize: 15,
                      fontWeight: 500,
                      cursor: ddCompany.trim() ? "pointer" : "default",
                      fontFamily: "inherit",
                      transition: "opacity 0.15s",
                    }}
                  >
                    Generate Report
                  </button>
                </div>

                <p style={{ fontSize: 12, color: "#1e2030", marginTop: 16 }}>
                  Analyses ~10 sections · Sources exclusively from BRSR index
                </p>
              </div>
            )}

            {/* Loading state */}
            {ddLoading && (
              <div style={{ maxWidth: 560, margin: "auto", width: "100%", textAlign: "center" }}>
                <div style={{ display: "flex", justifyContent: "center", gap: 6, marginBottom: 20 }}>
                  {[0, 1, 2, 3].map((i) => (
                    <div
                      key={i}
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: "50%",
                        background: "#6366f1",
                        animation: `pulse 1.4s ease-in-out ${i * 0.25}s infinite`,
                      }}
                    />
                  ))}
                </div>
                <p style={{ fontSize: 15, color: "#64748b", margin: "0 0 6px" }}>Analysing</p>
                <p style={{ fontSize: 17, color: "#94a3b8", fontWeight: 500, margin: 0, letterSpacing: "-0.01em" }}>
                  {DD_SECTIONS[ddSectionIdx]}
                </p>
                <p style={{ fontSize: 13, color: "#334155", marginTop: 24 }}>
                  Querying {DD_SECTIONS.length} report sections from the BRSR index…
                </p>
              </div>
            )}

            {/* Report state */}
            {ddReport && !ddLoading && (
              <div style={{ maxWidth: 860, margin: "0 auto", width: "100%" }}>
                {/* Report header */}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24, flexWrap: "wrap", gap: 12 }}>
                  <div>
                    <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.1em", color: "#475569", marginBottom: 4 }}>Due Diligence Report</div>
                    <h2 style={{ margin: 0, fontSize: 26, fontWeight: 600, color: "#e2e8f0", letterSpacing: "-0.02em" }}>
                      {ddReport.company}
                      {ddReport.symbol && <span style={{ fontSize: 16, color: "#6366f1", marginLeft: 10, fontWeight: 400 }}>{ddReport.symbol}</span>}
                    </h2>
                  </div>
                  <div style={{ display: "flex", gap: 10 }}>
                    {ddReport.total_sources > 0 && (
                      <button
                        onClick={() => {
                          if (activeSources) {
                            setActiveSources(null);
                          } else {
                            const allSrcs: Source[] = [];
                            const seen = new Set<string>();
                            for (const sec of ddReport.sections) {
                              for (const src of sec.sources) {
                                if (!seen.has(src.chunk_id)) {
                                  seen.add(src.chunk_id);
                                  allSrcs.push(src);
                                }
                              }
                            }
                            setActiveSources({ label: `${ddReport.total_sources} BRSR sources`, sources: allSrcs });
                          }
                        }}
                        style={{ fontSize: 14, color: "#6366f1", background: "none", border: "1px solid #312e81", borderRadius: 6, padding: "7px 16px", cursor: "pointer", fontFamily: "inherit" }}
                      >
                        {activeSources ? "Hide" : "View"} {ddReport.total_sources} sources
                      </button>
                    )}
                  </div>
                </div>

                {/* Section quick-nav pills */}
                {ddReport.sections.length > 0 && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 24 }}>
                    {ddReport.sections.map((sec) => (
                      <span
                        key={sec.title}
                        style={{
                          fontSize: 13,
                          background: sec.chunk_count > 0 ? "#1e1b4b" : "#0f1117",
                          color: sec.chunk_count > 0 ? "#818cf8" : "#334155",
                          border: "1px solid",
                          borderColor: sec.chunk_count > 0 ? "#312e81" : "#1e2030",
                          borderRadius: 20,
                          padding: "3px 10px",
                        }}
                      >
                        {sec.title} <span style={{ opacity: 0.6 }}>({sec.chunk_count})</span>
                      </span>
                    ))}
                  </div>
                )}

                {/* Markdown report body */}
                <div style={{ background: "#0f1117", border: "1px solid #1e2030", borderRadius: 12, padding: "32px 36px", fontSize: 15, lineHeight: 1.8 }}>
                  <MarkdownMessage content={ddReport.report_markdown} />
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {/* ── Right panel: sources (shared) ── */}
      <aside style={{ width: activeSources ? 340 : 0, borderLeft: activeSources ? "1px solid #1e2030" : "none", overflow: "hidden", transition: "width 0.25s ease", flexShrink: 0, display: "flex", flexDirection: "column" }}>
        {activeSources && (
          <>
            <div style={{ padding: "16px 20px", borderBottom: "1px solid #1e2030", display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 500 }}>Source Chunks</div>
                <div style={{ fontSize: 12, color: "#475569" }}>{activeSources.label}</div>
              </div>
              <button onClick={() => setActiveSources(null)} style={{ background: "none", border: "none", cursor: "pointer", color: "#475569", padding: 4 }}>
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
              </button>
            </div>

            <div style={{ flex: 1, overflowY: "auto", padding: "16px 16px" }}>
              {activeSources.sources.map((src, i) => (
                <div key={`${src.chunk_id}-${i}`} style={{ marginBottom: 12, background: "#0f1117", border: "1px solid #1e2030", borderRadius: 8, overflow: "hidden" }}>
                  <div style={{ padding: "10px 14px", borderBottom: "1px solid #1e2030", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <span style={{ fontSize: 11, background: src.collection.includes("narrative") ? "#1e1b4b" : "#052e16", color: src.collection.includes("narrative") ? "#818cf8" : "#4ade80", padding: "2px 8px", borderRadius: 4, fontFamily: "var(--font-mono)", letterSpacing: "0.02em" }}>
                        {collectionLabel(src.collection)}
                      </span>
                      <span style={{ fontSize: 11, color: "#334155" }}>#{i + 1}</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <div style={{ width: 6, height: 6, borderRadius: "50%", background: scoreColor(src.score) }} />
                      <span style={{ fontSize: 11, color: "#475569", fontFamily: "var(--font-mono)" }}>{(src.score * 100).toFixed(0)}%</span>
                    </div>
                  </div>

                  <div style={{ padding: "8px 14px", display: "flex", flexWrap: "wrap", gap: 4, borderBottom: "1px solid #1e2030" }}>
                    {Object.entries(src.metadata)
                      .filter(([k, v]) => v && !["strategy", "source_file", "row_count"].includes(k))
                      .slice(0, 5)
                      .map(([k, v]) => (
                        <span key={k} style={{ fontSize: 11, background: "#0a0a0f", border: "1px solid #1e2030", borderRadius: 4, padding: "2px 8px", color: "#475569" }}>
                          <span style={{ color: "#334155" }}>{k}:</span> {String(v)}
                        </span>
                      ))}
                  </div>

                  <div style={{ padding: "10px 14px", fontSize: 12.5, color: "#475569", lineHeight: 1.65, maxHeight: 160, overflowY: "auto", fontFamily: src.collection.includes("numerical") ? "var(--font-mono)" : "inherit" }}>
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
