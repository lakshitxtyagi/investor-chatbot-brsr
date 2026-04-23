"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type MetricValue = {
  display: string;
  raw: number | null;
};

type CompareMetric = {
  label: string;
  c1: MetricValue;
  c2: MetricValue;
  winner: "c1" | "c2" | null;
  lower_is_better: boolean;
};

type CompareSection = {
  title: string;
  metrics: CompareMetric[];
};

type CompanyMeta = {
  symbol: string;
  name: string;
};

type CompareResult = {
  company1: CompanyMeta;
  company2: CompanyMeta;
  sections: CompareSection[];
};

// ---------------------------------------------------------------------------
// Section icons
// ---------------------------------------------------------------------------

const SECTION_ICONS: Record<string, string> = {
  "Company Overview": "🏢",
  "Financial Performance": "💰",
  Workforce: "👥",
  "Health & Safety": "🛡️",
  "GHG Emissions": "🌫️",
  "Energy Consumption": "⚡",
  "Water Management": "💧",
  "Waste Management": "♻️",
  "Governance & Compliance": "⚖️",
  CSR: "🤝",
};

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const COLORS = {
  bg: "#0f1117",
  surface: "#1a1f2e",
  surfaceHover: "#222840",
  border: "#2a3050",
  accent: "#6366f1",
  accentLight: "rgba(99,102,241,0.15)",
  win: "#22c55e",
  winBg: "rgba(34,197,94,0.1)",
  lose: "#ef4444",
  loseBg: "rgba(239,68,68,0.07)",
  neutral: "#64748b",
  text: "#e2e8f0",
  textMuted: "#94a3b8",
  textDim: "#475569",
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function CompanyInput({
  label,
  value,
  onChange,
  symbols,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  symbols: string[];
  placeholder: string;
}) {
  const [open, setOpen] = useState(false);
  const [filtered, setFiltered] = useState<string[]>([]);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleInput = (v: string) => {
    onChange(v);
    const upper = v.toUpperCase();
    setFiltered(symbols.filter((s) => s.includes(upper)).slice(0, 12));
    setOpen(v.length > 0);
  };

  return (
    <div ref={ref} style={{ position: "relative", flex: 1 }}>
      <label
        style={{
          display: "block",
          fontSize: 13,
          fontWeight: 600,
          color: COLORS.textMuted,
          marginBottom: 6,
          letterSpacing: "0.05em",
          textTransform: "uppercase",
        }}
      >
        {label}
      </label>
      <input
        value={value}
        onChange={(e) => handleInput(e.target.value)}
        onFocus={() => {
          const upper = value.toUpperCase();
          setFiltered(symbols.filter((s) => s.includes(upper)).slice(0, 12));
          if (value.length > 0) setOpen(true);
        }}
        placeholder={placeholder}
        style={{
          width: "100%",
          padding: "12px 16px",
          background: COLORS.surface,
          border: `1.5px solid ${COLORS.border}`,
          borderRadius: 10,
          color: COLORS.text,
          fontSize: 17,
          fontWeight: 500,
          outline: "none",
          boxSizing: "border-box",
          transition: "border-color 0.2s",
        }}
        onMouseOver={(e) =>
          ((e.target as HTMLInputElement).style.borderColor = COLORS.accent)
        }
        onMouseOut={(e) =>
          ((e.target as HTMLInputElement).style.borderColor = COLORS.border)
        }
      />
      {open && filtered.length > 0 && (
        <div
          style={{
            position: "absolute",
            top: "100%",
            left: 0,
            right: 0,
            background: COLORS.surface,
            border: `1px solid ${COLORS.border}`,
            borderRadius: 8,
            zIndex: 100,
            maxHeight: 220,
            overflowY: "auto",
            marginTop: 4,
            boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
          }}
        >
          {filtered.map((s) => (
            <div
              key={s}
              onClick={() => {
                onChange(s);
                setOpen(false);
              }}
              style={{
                padding: "10px 16px",
                fontSize: 15,
                color: COLORS.text,
                cursor: "pointer",
                fontFamily: "monospace",
                transition: "background 0.15s",
              }}
              onMouseOver={(e) =>
                ((e.currentTarget as HTMLElement).style.background =
                  COLORS.accentLight)
              }
              onMouseOut={(e) =>
                ((e.currentTarget as HTMLElement).style.background =
                  "transparent")
              }
            >
              {s}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function MetricRow({
  metric,
  idx,
}: {
  metric: CompareMetric;
  idx: number;
}) {
  const isLabel = metric.c1.raw === null && metric.c2.raw === null;
  const c1Win = metric.winner === "c1";
  const c2Win = metric.winner === "c2";
  const isSubrow = metric.label.startsWith("  ");

  if (isLabel) {
    return (
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: 8,
          padding: "10px 16px",
          background: idx % 2 === 0 ? "rgba(255,255,255,0.01)" : "transparent",
          borderRadius: 6,
        }}
      >
        <div
          style={{
            fontSize: isSubrow ? 14 : 15,
            color: isSubrow ? COLORS.textMuted : COLORS.text,
            paddingLeft: isSubrow ? 16 : 0,
          }}
        >
          {metric.label}
        </div>
        <div style={{ fontSize: 15, color: COLORS.text, fontWeight: 500 }}>
          {metric.c1.display}
        </div>
        <div style={{ fontSize: 15, color: COLORS.text, fontWeight: 500 }}>
          {metric.c2.display}
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr 1fr",
        gap: 8,
        padding: "10px 16px",
        background: idx % 2 === 0 ? "rgba(255,255,255,0.015)" : "transparent",
        borderRadius: 6,
        transition: "background 0.15s",
      }}
      onMouseOver={(e) =>
        ((e.currentTarget as HTMLElement).style.background = COLORS.surfaceHover)
      }
      onMouseOut={(e) =>
        ((e.currentTarget as HTMLElement).style.background =
          idx % 2 === 0 ? "rgba(255,255,255,0.015)" : "transparent")
      }
    >
      {/* Label */}
      <div
        style={{
          fontSize: isSubrow ? 14 : 15,
          color: isSubrow ? COLORS.textMuted : COLORS.text,
          display: "flex",
          alignItems: "center",
          gap: 6,
          paddingLeft: isSubrow ? 16 : 0,
        }}
      >
        {metric.label}
      </div>

      {/* C1 */}
      <div
        style={{
          fontSize: 15,
          fontWeight: 600,
          color: c1Win ? COLORS.win : c2Win ? COLORS.lose : COLORS.text,
          background: c1Win
            ? COLORS.winBg
            : c2Win
            ? COLORS.loseBg
            : "transparent",
          borderRadius: 6,
          padding: c1Win || c2Win ? "2px 8px" : 0,
          display: "inline-flex",
          alignItems: "center",
          gap: 4,
        }}
      >
        {c1Win && <span style={{ fontSize: 11 }}>▲</span>}
        {c2Win && <span style={{ fontSize: 11 }}>▼</span>}
        {metric.c1.display}
      </div>

      {/* C2 */}
      <div
        style={{
          fontSize: 15,
          fontWeight: 600,
          color: c2Win ? COLORS.win : c1Win ? COLORS.lose : COLORS.text,
          background: c2Win
            ? COLORS.winBg
            : c1Win
            ? COLORS.loseBg
            : "transparent",
          borderRadius: 6,
          padding: c1Win || c2Win ? "2px 8px" : 0,
          display: "inline-flex",
          alignItems: "center",
          gap: 4,
        }}
      >
        {c2Win && <span style={{ fontSize: 11 }}>▲</span>}
        {c1Win && <span style={{ fontSize: 11 }}>▼</span>}
        {metric.c2.display}
      </div>
    </div>
  );
}

function SectionCard({
  section,
  c1Name,
  c2Name,
}: {
  section: CompareSection;
  c1Name: string;
  c2Name: string;
}) {
  const [open, setOpen] = useState(true);
  const icon = SECTION_ICONS[section.title] || "📊";

  const c1Wins = section.metrics.filter((m) => m.winner === "c1").length;
  const c2Wins = section.metrics.filter((m) => m.winner === "c2").length;

  return (
    <div
      style={{
        background: COLORS.surface,
        borderRadius: 14,
        border: `1px solid ${COLORS.border}`,
        overflow: "hidden",
        marginBottom: 16,
      }}
    >
      {/* Section header */}
      <button
        onClick={() => setOpen(!open)}
        style={{
          width: "100%",
          background: "none",
          border: "none",
          padding: "16px 20px",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: 12,
          textAlign: "left",
        }}
      >
        <span style={{ fontSize: 22 }}>{icon}</span>
        <span
          style={{ flex: 1, fontSize: 18, fontWeight: 700, color: COLORS.text }}
        >
          {section.title}
        </span>
        {(c1Wins > 0 || c2Wins > 0) && (
          <div style={{ display: "flex", gap: 8, marginRight: 12 }}>
            {c1Wins > 0 && (
              <span
                style={{
                  background: COLORS.winBg,
                  color: COLORS.win,
                  fontSize: 13,
                  fontWeight: 600,
                  padding: "3px 10px",
                  borderRadius: 20,
                  border: `1px solid ${COLORS.win}40`,
                }}
              >
                {c1Name.split(" ")[0]} +{c1Wins}
              </span>
            )}
            {c2Wins > 0 && (
              <span
                style={{
                  background: COLORS.winBg,
                  color: COLORS.win,
                  fontSize: 13,
                  fontWeight: 600,
                  padding: "3px 10px",
                  borderRadius: 20,
                  border: `1px solid ${COLORS.win}40`,
                }}
              >
                {c2Name.split(" ")[0]} +{c2Wins}
              </span>
            )}
          </div>
        )}
        <span
          style={{
            fontSize: 18,
            color: COLORS.textMuted,
            transform: open ? "rotate(180deg)" : "none",
            transition: "transform 0.2s",
          }}
        >
          ▾
        </span>
      </button>

      {open && (
        <div style={{ borderTop: `1px solid ${COLORS.border}` }}>
          {/* Column headers */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1fr",
              gap: 8,
              padding: "10px 16px 6px",
              borderBottom: `1px solid ${COLORS.border}40`,
            }}
          >
            <div
              style={{
                fontSize: 13,
                fontWeight: 700,
                color: COLORS.textDim,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
              }}
            >
              Metric
            </div>
            <div
              style={{
                fontSize: 13,
                fontWeight: 700,
                color: COLORS.accent,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
              }}
            >
              {c1Name}
            </div>
            <div
              style={{
                fontSize: 13,
                fontWeight: 700,
                color: "#a78bfa",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
              }}
            >
              {c2Name}
            </div>
          </div>

          <div style={{ padding: "8px 0 12px" }}>
            {section.metrics.map((metric, i) => (
              <MetricRow key={i} metric={metric} idx={i} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Scorecard summary
// ---------------------------------------------------------------------------

function Scorecard({
  result,
}: {
  result: CompareResult;
}) {
  let c1Total = 0;
  let c2Total = 0;
  result.sections.forEach((s) => {
    s.metrics.forEach((m) => {
      if (m.winner === "c1") c1Total++;
      if (m.winner === "c2") c2Total++;
    });
  });
  const total = c1Total + c2Total;

  return (
    <div
      style={{
        background: COLORS.surface,
        borderRadius: 14,
        border: `1px solid ${COLORS.border}`,
        padding: "20px 24px",
        marginBottom: 24,
        display: "flex",
        alignItems: "center",
        gap: 24,
        flexWrap: "wrap",
      }}
    >
      <div style={{ flex: 1, minWidth: 200 }}>
        <div
          style={{
            fontSize: 13,
            color: COLORS.textMuted,
            marginBottom: 4,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
          }}
        >
          Overall Scorecard
        </div>
        <div
          style={{
            fontSize: 15,
            color: COLORS.textMuted,
          }}
        >
          {total > 0 ? `${total} metrics compared across ${result.sections.length} sections` : "No comparable numeric metrics found"}
        </div>
      </div>

      {/* Bar */}
      <div style={{ flex: 2, minWidth: 300 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginBottom: 6,
          }}
        >
          <span style={{ fontSize: 15, fontWeight: 700, color: COLORS.accent }}>
            {result.company1.symbol} — {c1Total} wins
          </span>
          <span style={{ fontSize: 15, fontWeight: 700, color: "#a78bfa" }}>
            {result.company2.symbol} — {c2Total} wins
          </span>
        </div>
        <div
          style={{
            height: 12,
            background: COLORS.border,
            borderRadius: 6,
            overflow: "hidden",
            display: "flex",
          }}
        >
          {total > 0 && (
            <>
              <div
                style={{
                  width: `${(c1Total / total) * 100}%`,
                  background: COLORS.accent,
                  transition: "width 0.6s ease",
                }}
              />
              <div
                style={{
                  width: `${(c2Total / total) * 100}%`,
                  background: "#a78bfa",
                  transition: "width 0.6s ease",
                }}
              />
            </>
          )}
        </div>
        {total > 0 && (
          <div style={{ marginTop: 6, textAlign: "center", fontSize: 13, color: COLORS.textMuted }}>
            {c1Total > c2Total
              ? `${result.company1.name} leads overall`
              : c2Total > c1Total
              ? `${result.company2.name} leads overall`
              : "Tied"}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function ComparePage() {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [c1, setC1] = useState("");
  const [c2, setC2] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CompareResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("http://localhost:8000/compare/symbols")
      .then((r) => r.json())
      .then((d) => setSymbols(d.symbols || []))
      .catch(() => {});
  }, []);

  const handleCompare = async () => {
    if (!c1.trim() || !c2.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch("http://localhost:8000/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ company1: c1.trim(), company2: c2.trim() }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Comparison failed");
      }
      setResult(await res.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: COLORS.bg,
        color: COLORS.text,
        fontFamily:
          "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      }}
    >
      {/* Nav */}
      <nav
        style={{
          padding: "0 32px",
          height: 60,
          display: "flex",
          alignItems: "center",
          borderBottom: `1px solid ${COLORS.border}`,
          background: COLORS.surface,
          position: "sticky",
          top: 0,
          zIndex: 200,
          gap: 24,
        }}
      >
        <Link
          href="/"
          style={{
            textDecoration: "none",
            color: COLORS.text,
            fontWeight: 700,
            fontSize: 18,
            letterSpacing: "-0.02em",
          }}
        >
          <span style={{ color: COLORS.accent }}>BRSR</span> Analytics
        </Link>
        <div style={{ flex: 1 }} />
        <Link
          href="/"
          style={{
            fontSize: 15,
            color: COLORS.textMuted,
            textDecoration: "none",
          }}
        >
          Dashboard
        </Link>
        <Link
          href="/research"
          style={{
            fontSize: 15,
            color: COLORS.textMuted,
            textDecoration: "none",
          }}
        >
          Research
        </Link>
        <span
          style={{
            fontSize: 15,
            color: COLORS.accent,
            fontWeight: 600,
            borderBottom: `2px solid ${COLORS.accent}`,
            paddingBottom: 2,
          }}
        >
          Compare
        </span>
      </nav>

      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "32px 24px" }}>
        {/* Header */}
        <div style={{ marginBottom: 32 }}>
          <h1
            style={{
              fontSize: 32,
              fontWeight: 800,
              margin: "0 0 8px",
              letterSpacing: "-0.03em",
            }}
          >
            Company ESG Comparison
          </h1>
          <p style={{ fontSize: 17, color: COLORS.textMuted, margin: 0 }}>
            Side-by-side analysis from BRSR disclosures. Select two companies to compare across 10 ESG dimensions.
          </p>
        </div>

        {/* Input row */}
        <div
          style={{
            background: COLORS.surface,
            borderRadius: 14,
            border: `1px solid ${COLORS.border}`,
            padding: "24px",
            marginBottom: 28,
          }}
        >
          <div style={{ display: "flex", gap: 16, alignItems: "flex-end", flexWrap: "wrap" }}>
            <CompanyInput
              label="Company 1"
              value={c1}
              onChange={setC1}
              symbols={symbols}
              placeholder="e.g. INFY"
            />
            <div
              style={{
                fontSize: 22,
                color: COLORS.textDim,
                padding: "0 8px",
                marginBottom: 8,
                flexShrink: 0,
              }}
            >
              vs
            </div>
            <CompanyInput
              label="Company 2"
              value={c2}
              onChange={setC2}
              symbols={symbols}
              placeholder="e.g. TCS"
            />
            <button
              onClick={handleCompare}
              disabled={loading || !c1.trim() || !c2.trim()}
              style={{
                padding: "12px 28px",
                background:
                  loading || !c1.trim() || !c2.trim()
                    ? COLORS.border
                    : COLORS.accent,
                color: "white",
                border: "none",
                borderRadius: 10,
                fontSize: 16,
                fontWeight: 700,
                cursor:
                  loading || !c1.trim() || !c2.trim() ? "not-allowed" : "pointer",
                whiteSpace: "nowrap",
                flexShrink: 0,
                transition: "background 0.2s",
                marginBottom: 2,
              }}
            >
              {loading ? "Comparing…" : "Compare ↗"}
            </button>
          </div>

          {/* Quick picks */}
          <div style={{ marginTop: 14, display: "flex", gap: 8, flexWrap: "wrap" }}>
            <span style={{ fontSize: 13, color: COLORS.textDim, marginRight: 4 }}>
              Quick picks:
            </span>
            {[
              ["INFY", "TCS"],
              ["INFY", "WIPRO"],
              ["TATASTEEL", "JSWSTEEL"],
              ["HDFCBANK", "ICICIBANK"],
            ].map(([a, b]) => (
              <button
                key={`${a}-${b}`}
                onClick={() => {
                  setC1(a);
                  setC2(b);
                }}
                style={{
                  padding: "4px 12px",
                  background: COLORS.accentLight,
                  border: `1px solid ${COLORS.accent}40`,
                  borderRadius: 20,
                  color: COLORS.accent,
                  fontSize: 13,
                  cursor: "pointer",
                  fontWeight: 500,
                }}
              >
                {a} vs {b}
              </button>
            ))}
          </div>
        </div>

        {/* Error */}
        {error && (
          <div
            style={{
              background: "rgba(239,68,68,0.1)",
              border: "1px solid rgba(239,68,68,0.3)",
              borderRadius: 10,
              padding: "16px 20px",
              color: "#fca5a5",
              marginBottom: 24,
              fontSize: 15,
            }}
          >
            ⚠ {error}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div
            style={{
              textAlign: "center",
              padding: "60px 0",
              color: COLORS.textMuted,
            }}
          >
            <div
              style={{
                width: 48,
                height: 48,
                border: `4px solid ${COLORS.border}`,
                borderTop: `4px solid ${COLORS.accent}`,
                borderRadius: "50%",
                margin: "0 auto 16px",
                animation: "spin 0.8s linear infinite",
              }}
            />
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            <div style={{ fontSize: 17, fontWeight: 500 }}>
              Loading BRSR data…
            </div>
            <div style={{ fontSize: 14, marginTop: 6 }}>
              Extracting metrics from CSV files
            </div>
          </div>
        )}

        {/* Results */}
        {result && !loading && (
          <>
            {/* Company name banner */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 16,
                marginBottom: 20,
              }}
            >
              {[result.company1, result.company2].map((co, i) => (
                <div
                  key={i}
                  style={{
                    background: COLORS.surface,
                    borderRadius: 12,
                    border: `1px solid ${i === 0 ? COLORS.accent : "#a78bfa"}40`,
                    padding: "16px 20px",
                    display: "flex",
                    alignItems: "center",
                    gap: 14,
                  }}
                >
                  <div
                    style={{
                      width: 44,
                      height: 44,
                      borderRadius: 10,
                      background: i === 0 ? COLORS.accentLight : "rgba(167,139,250,0.15)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 15,
                      fontWeight: 800,
                      color: i === 0 ? COLORS.accent : "#a78bfa",
                      letterSpacing: "-0.02em",
                    }}
                  >
                    {co.symbol.slice(0, 3)}
                  </div>
                  <div>
                    <div
                      style={{
                        fontSize: 11,
                        color: COLORS.textDim,
                        textTransform: "uppercase",
                        letterSpacing: "0.07em",
                        marginBottom: 2,
                      }}
                    >
                      Company {i + 1}
                    </div>
                    <div
                      style={{
                        fontSize: 17,
                        fontWeight: 700,
                        color: COLORS.text,
                      }}
                    >
                      {co.name}
                    </div>
                    <div
                      style={{
                        fontSize: 13,
                        color: i === 0 ? COLORS.accent : "#a78bfa",
                        fontWeight: 600,
                      }}
                    >
                      {co.symbol}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <Scorecard result={result} />

            {result.sections.map((section, i) => (
              <SectionCard
                key={i}
                section={section}
                c1Name={result.company1.symbol}
                c2Name={result.company2.symbol}
              />
            ))}

            <div
              style={{
                textAlign: "center",
                padding: "24px 0 8px",
                fontSize: 13,
                color: COLORS.textDim,
              }}
            >
              Data sourced directly from BRSR disclosures (FY 2024–25) · Green ▲ = better · Red ▼ = worse
            </div>
          </>
        )}

        {/* Empty state */}
        {!result && !loading && !error && (
          <div
            style={{
              textAlign: "center",
              padding: "64px 0",
              color: COLORS.textMuted,
            }}
          >
            <div style={{ fontSize: 48, marginBottom: 16 }}>📊</div>
            <div style={{ fontSize: 20, fontWeight: 600, marginBottom: 8 }}>
              Select two companies to begin
            </div>
            <div style={{ fontSize: 15 }}>
              Type a BSE/NSE symbol (e.g. INFY, TCS, WIPRO) or pick a quick comparison above
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
