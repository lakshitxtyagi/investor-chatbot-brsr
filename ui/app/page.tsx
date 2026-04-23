"use client";

import { useState } from "react";
import Link from "next/link";

// ─── Static mock data ────────────────────────────────────────────────────────

const SECTORS = ["All", "Manufacturing", "IT & Software", "Energy", "FMCG", "Financial"];

const COMPANIES = [
  {
    id: "tcs",
    name: "Tata Consultancy Services",
    ticker: "TCS",
    sector: "IT & Software",
    score: 87,
    grade: "A",
    ghg: 1.2,
    water: 3.4,
    energy: 12.1,
    waste: 0.8,
    renewableShare: 68,
    trend: "up",
    fy: "FY2023",
    principles: { compliant: 8, partial: 1, violated: 0 },
    highlights: ["Net-zero target 2030", "68% renewable energy", "ISO 14001 certified"],
  },
  {
    id: "infosys",
    name: "Infosys",
    ticker: "INFY",
    sector: "IT & Software",
    score: 91,
    grade: "A+",
    ghg: 0.9,
    water: 2.8,
    energy: 9.4,
    waste: 0.5,
    renewableShare: 82,
    trend: "up",
    fy: "FY2023",
    principles: { compliant: 9, partial: 0, violated: 0 },
    highlights: ["Carbon neutral since 2020", "82% renewable energy", "Water positive"],
  },
  {
    id: "wipro",
    name: "Wipro",
    ticker: "WIPRO",
    sector: "IT & Software",
    score: 83,
    grade: "A-",
    ghg: 1.5,
    water: 4.1,
    energy: 14.2,
    waste: 1.1,
    renewableShare: 55,
    trend: "up",
    fy: "FY2023",
    principles: { compliant: 8, partial: 1, violated: 0 },
    highlights: ["Net-zero target 2040", "55% renewable energy", "Zero waste to landfill"],
  },
  {
    id: "tatasteel",
    name: "Tata Steel",
    ticker: "TATASTEEL",
    sector: "Manufacturing",
    score: 64,
    grade: "B",
    ghg: 38.4,
    water: 22.6,
    energy: 187.3,
    waste: 14.2,
    renewableShare: 18,
    trend: "neutral",
    fy: "FY2023",
    principles: { compliant: 5, partial: 3, violated: 1 },
    highlights: ["Targeting 30% emissions cut by 2030", "18% renewable energy", "Blast furnace transition plan"],
  },
  {
    id: "jsw",
    name: "JSW Steel",
    ticker: "JSWSTEEL",
    sector: "Manufacturing",
    score: 58,
    grade: "B-",
    ghg: 42.1,
    water: 28.3,
    energy: 204.7,
    waste: 18.6,
    renewableShare: 12,
    trend: "down",
    fy: "FY2023",
    principles: { compliant: 4, partial: 4, violated: 1 },
    highlights: ["Scrap-based EAF expansion", "12% renewable energy", "Water recycling upgrades"],
  },
  {
    id: "reliance",
    name: "Reliance Industries",
    ticker: "RELIANCE",
    sector: "Energy",
    score: 72,
    grade: "B+",
    ghg: 68.2,
    water: 41.5,
    energy: 312.8,
    waste: 22.1,
    renewableShare: 9,
    trend: "up",
    fy: "FY2023",
    principles: { compliant: 6, partial: 2, violated: 1 },
    highlights: ["₹75,000 Cr green energy investment", "New Energy business launch", "Solar giga-factory"],
  },
  {
    id: "hul",
    name: "HUL",
    ticker: "HINDUNILVR",
    sector: "FMCG",
    score: 79,
    grade: "B+",
    ghg: 2.1,
    water: 5.8,
    energy: 18.4,
    waste: 0.6,
    renewableShare: 44,
    trend: "up",
    fy: "FY2023",
    principles: { compliant: 7, partial: 2, violated: 0 },
    highlights: ["Plastic-neutral target", "44% renewable energy", "Sustainable sourcing 95%"],
  },
  {
    id: "hdfc",
    name: "HDFC Bank",
    ticker: "HDFCBANK",
    sector: "Financial",
    score: 76,
    grade: "B+",
    ghg: 0.4,
    water: 0.9,
    energy: 3.2,
    waste: 0.1,
    renewableShare: 31,
    trend: "neutral",
    fy: "FY2023",
    principles: { compliant: 7, partial: 2, violated: 0 },
    highlights: ["Green building certified HQ", "31% renewable energy", "ESG-linked lending"],
  },
];

const SECTOR_STATS = {
  "IT & Software": { avgScore: 87, avgGhg: 1.2, color: "#6366f1", companies: 3 },
  Manufacturing: { avgScore: 61, avgGhg: 40.3, color: "#f59e0b", companies: 2 },
  Energy: { avgScore: 72, avgGhg: 68.2, color: "#ef4444", companies: 1 },
  FMCG: { avgScore: 79, avgGhg: 2.1, color: "#22c55e", companies: 1 },
  Financial: { avgScore: 76, avgGhg: 0.4, color: "#22d3ee", companies: 1 },
};

// ─── Sub-components ───────────────────────────────────────────────────────────

function GradeChip({ grade }: { grade: string }) {
  const colors: Record<string, { bg: string; color: string }> = {
    "A+": { bg: "#052e16", color: "#4ade80" },
    A: { bg: "#052e16", color: "#86efac" },
    "A-": { bg: "#052e16", color: "#bbf7d0" },
    "B+": { bg: "#1e293b", color: "#93c5fd" },
    B: { bg: "#1e293b", color: "#bfdbfe" },
    "B-": { bg: "#2d1b00", color: "#fbbf24" },
    C: { bg: "#2d0a0a", color: "#f87171" },
  };
  const c = colors[grade] || { bg: "#1e2030", color: "#94a3b8" };
  return (
    <span style={{ fontSize: 14, fontWeight: 700, padding: "3px 9px", borderRadius: 5, background: c.bg, color: c.color, letterSpacing: "0.04em" }}>
      {grade}
    </span>
  );
}

function TrendIcon({ trend }: { trend: string }) {
  if (trend === "up") return <svg width="13" height="13" viewBox="0 0 12 12" fill="none"><path d="M2 9L6 3l4 6" stroke="#22c55e" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>;
  if (trend === "down") return <svg width="13" height="13" viewBox="0 0 12 12" fill="none"><path d="M2 3L6 9l4-6" stroke="#ef4444" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>;
  return <svg width="13" height="13" viewBox="0 0 12 12" fill="none"><path d="M2 6h8" stroke="#94a3b8" strokeWidth="1.5" strokeLinecap="round" /></svg>;
}

function ScoreBar({ value, max = 100, color = "#6366f1" }: { value: number; max?: number; color?: string }) {
  return (
    <div style={{ width: "100%", height: 3, background: "#1e2030", borderRadius: 2, overflow: "hidden" }}>
      <div style={{ width: `${(value / max) * 100}%`, height: "100%", background: color, borderRadius: 2, transition: "width 0.6s ease" }} />
    </div>
  );
}

function CompanyCard({ company, onClick, selected }: { company: typeof COMPANIES[0]; onClick: () => void; selected: boolean }) {
  const sectorColor = SECTOR_STATS[company.sector as keyof typeof SECTOR_STATS]?.color ?? "#6366f1";

  return (
    <div
      onClick={onClick}
      style={{
        background: selected ? "#0f1117" : "#0a0a0f",
        border: `1px solid ${selected ? "#6366f1" : "#1e2030"}`,
        borderRadius: 10,
        padding: "18px",
        cursor: "pointer",
        transition: "all 0.15s ease",
        position: "relative",
        overflow: "hidden",
      }}
      onMouseEnter={(e) => { if (!selected) e.currentTarget.style.borderColor = "#334155"; }}
      onMouseLeave={(e) => { if (!selected) e.currentTarget.style.borderColor = "#1e2030"; }}
    >
      {/* Top row */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 14 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 4 }}>
            <span style={{ fontSize: 17, fontWeight: 600, color: "#e2e8f0" }}>{company.ticker}</span>
            <TrendIcon trend={company.trend} />
          </div>
          <div style={{ fontSize: 14, color: "#475569", maxWidth: 160, lineHeight: 1.4 }}>{company.name}</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 5 }}>
          <GradeChip grade={company.grade} />
          <span style={{ fontSize: 13, color: sectorColor, background: `${sectorColor}18`, padding: "2px 7px", borderRadius: 4 }}>{company.sector}</span>
        </div>
      </div>

      {/* ESG Score */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
          <span style={{ fontSize: 13, color: "#475569", textTransform: "uppercase", letterSpacing: "0.08em" }}>ESG Score</span>
          <span style={{ fontSize: 16, fontWeight: 600, color: "#e2e8f0" }}>{company.score}</span>
        </div>
        <ScoreBar value={company.score} color={sectorColor} />
      </div>

      {/* Metrics row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
        {[
          { label: "GHG", value: company.ghg, unit: "Mt" },
          { label: "Water", value: company.water, unit: "Mm³" },
          { label: "Renew.", value: company.renewableShare, unit: "%" },
        ].map((m) => (
          <div key={m.label} style={{ background: "#060608", border: "1px solid #1a1a2e", borderRadius: 6, padding: "7px 9px" }}>
            <div style={{ fontSize: 12, color: "#334155", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 3 }}>{m.label}</div>
            <div style={{ fontSize: 15, fontWeight: 600, color: "#94a3b8" }}>{m.value}<span style={{ fontSize: 12, color: "#334155", marginLeft: 2 }}>{m.unit}</span></div>
          </div>
        ))}
      </div>

      {/* Principles */}
      <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
        <span style={{ fontSize: 14, color: "#4ade80" }}>✓ {company.principles.compliant}</span>
        <span style={{ fontSize: 14, color: "#f59e0b" }}>~ {company.principles.partial}</span>
        <span style={{ fontSize: 14, color: "#ef4444" }}>✕ {company.principles.violated}</span>
        <span style={{ fontSize: 14, color: "#334155" }}>BRSR principles</span>
      </div>
    </div>
  );
}

function DetailPanel({ company, onClose }: { company: typeof COMPANIES[0]; onClose: () => void }) {
  const sectorColor = SECTOR_STATS[company.sector as keyof typeof SECTOR_STATS]?.color ?? "#6366f1";

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <div style={{ padding: "22px 24px 18px", borderBottom: "1px solid #1e2030", display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 5 }}>
            <span style={{ fontSize: 24, fontWeight: 700, color: "#e2e8f0" }}>{company.ticker}</span>
            <GradeChip grade={company.grade} />
          </div>
          <div style={{ fontSize: 15, color: "#475569" }}>{company.name} · {company.fy}</div>
        </div>
        <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "#475569", padding: 4 }}>
          <svg width="15" height="15" viewBox="0 0 16 16" fill="none"><path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
        </button>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px" }}>
        {/* Score gauge */}
        <div style={{ background: "#0f1117", border: "1px solid #1e2030", borderRadius: 10, padding: "18px", marginBottom: 18, textAlign: "center" }}>
          <div style={{ fontSize: 56, fontWeight: 800, color: sectorColor, lineHeight: 1, marginBottom: 5 }}>{company.score}</div>
          <div style={{ fontSize: 14, color: "#475569", textTransform: "uppercase", letterSpacing: "0.1em" }}>ESG Score / 100</div>
          <div style={{ marginTop: 14 }}>
            <ScoreBar value={company.score} color={sectorColor} />
          </div>
        </div>

        {/* Metrics */}
        <div style={{ fontSize: 14, textTransform: "uppercase", letterSpacing: "0.1em", color: "#334155", marginBottom: 10 }}>Key Metrics</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 18 }}>
          {[
            { label: "GHG Emissions", value: `${company.ghg} Mt CO₂e`, sub: "Scope 1+2" },
            { label: "Water Consumed", value: `${company.water} Mm³`, sub: "Total intensity" },
            { label: "Energy Used", value: `${company.energy} PJ`, sub: "Total" },
            { label: "Waste Generated", value: `${company.waste} Mt`, sub: "Total" },
            { label: "Renewable Mix", value: `${company.renewableShare}%`, sub: "Of total energy" },
            { label: "Trend", value: company.trend === "up" ? "↑ Improving" : company.trend === "down" ? "↓ Declining" : "→ Stable", sub: "YoY" },
          ].map((m) => (
            <div key={m.label} style={{ background: "#060608", border: "1px solid #1a1a2e", borderRadius: 8, padding: "11px 13px" }}>
              <div style={{ fontSize: 12, color: "#334155", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 5 }}>{m.label}</div>
              <div style={{ fontSize: 17, fontWeight: 600, color: "#e2e8f0", marginBottom: 3 }}>{m.value}</div>
              <div style={{ fontSize: 13, color: "#334155" }}>{m.sub}</div>
            </div>
          ))}
        </div>

        {/* BRSR Principles */}
        <div style={{ fontSize: 14, textTransform: "uppercase", letterSpacing: "0.1em", color: "#334155", marginBottom: 10 }}>BRSR Compliance (9 Principles)</div>
        <div style={{ background: "#0f1117", border: "1px solid #1e2030", borderRadius: 10, padding: "16px 18px", marginBottom: 18 }}>
          <div style={{ display: "flex", gap: 20, marginBottom: 12 }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: "#4ade80" }}>{company.principles.compliant}</div>
              <div style={{ fontSize: 13, color: "#475569" }}>Compliant</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: "#f59e0b" }}>{company.principles.partial}</div>
              <div style={{ fontSize: 13, color: "#475569" }}>Partial</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: "#ef4444" }}>{company.principles.violated}</div>
              <div style={{ fontSize: 13, color: "#475569" }}>Violated</div>
            </div>
          </div>
          <div style={{ display: "flex", gap: 2 }}>
            {Array.from({ length: 9 }).map((_, i) => {
              const isCompliant = i < company.principles.compliant;
              const isPartial = i < company.principles.compliant + company.principles.partial;
              return (
                <div key={i} style={{ flex: 1, height: 6, borderRadius: 2, background: isCompliant ? "#22c55e" : isPartial ? "#f59e0b" : "#ef4444" }} />
              );
            })}
          </div>
        </div>

        {/* Highlights */}
        <div style={{ fontSize: 14, textTransform: "uppercase", letterSpacing: "0.1em", color: "#334155", marginBottom: 10 }}>ESG Highlights</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 7, marginBottom: 26 }}>
          {company.highlights.map((h) => (
            <div key={h} style={{ display: "flex", alignItems: "center", gap: 9, background: "#0f1117", border: "1px solid #1e2030", borderRadius: 7, padding: "10px 13px" }}>
              <div style={{ width: 5, height: 5, borderRadius: "50%", background: sectorColor, flexShrink: 0 }} />
              <span style={{ fontSize: 15, color: "#94a3b8" }}>{h}</span>
            </div>
          ))}
        </div>

        {/* Research CTA */}
        <Link href="/research" style={{ textDecoration: "none" }}>
          <button style={{ width: "100%", padding: "13px", background: "linear-gradient(135deg,#6366f1,#22d3ee)", border: "none", borderRadius: 9, cursor: "pointer", fontSize: 16, fontWeight: 600, color: "white", letterSpacing: "0.01em" }}>
            Deep Research with AI →
          </button>
        </Link>
      </div>
    </div>
  );
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [sector, setSector] = useState("All");
  const [sort, setSort] = useState<"score" | "ghg" | "renewable">("score");
  const [selected, setSelected] = useState<typeof COMPANIES[0] | null>(null);
  const [search, setSearch] = useState("");

  const filtered = COMPANIES
    .filter((c) => sector === "All" || c.sector === sector)
    .filter((c) =>
      search === "" ||
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.ticker.toLowerCase().includes(search.toLowerCase())
    )
    .sort((a, b) => {
      if (sort === "score") return b.score - a.score;
      if (sort === "ghg") return a.ghg - b.ghg;
      if (sort === "renewable") return b.renewableShare - a.renewableShare;
      return 0;
    });

  return (
    <div style={{ display: "flex", height: "100vh", background: "#0a0a0f", color: "#e2e8f0", fontFamily: "var(--font-sans, DM Sans, sans-serif)", overflow: "hidden" }}>

      {/* ── Sidebar ── */}
      <aside style={{ width: 210, borderRight: "1px solid #1e2030", display: "flex", flexDirection: "column", padding: "24px 18px", flexShrink: 0 }}>
        <div style={{ marginBottom: 30 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 5 }}>
            <div style={{ width: 28, height: 28, borderRadius: 6, background: "linear-gradient(135deg,#6366f1,#22d3ee)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 12L6 4l4 6 2-3 2 5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
            </div>
            <span style={{ fontSize: 17, fontWeight: 600, letterSpacing: "-0.01em" }}>BRSR Analyst</span>
          </div>
          <p style={{ fontSize: 14, color: "#334155", margin: 0 }}>ESG Intelligence for Investors</p>
        </div>

        {/* Nav */}
        <div style={{ display: "flex", flexDirection: "column", gap: 2, marginBottom: "auto" }}>
          {[
            { label: "Dashboard", icon: "M2 12L6 4l4 6 2-3 2 5", active: true, href: "/" },
            { label: "Compare", icon: "M2 8h5M9 8h5M8 2v5M8 9v5", active: false, href: "/compare" },
            { label: "Research", icon: "M3 3h10v10H3zM3 7h10M7 3v10", active: false, href: "/research" },
            { label: "Alerts", icon: "M8 2a5 5 0 010 10A5 5 0 018 2zM8 14v1", active: false, href: "#" },
          ].map((item) => (
            <Link key={item.label} href={item.href} style={{ textDecoration: "none" }}>
              <div
                style={{ display: "flex", alignItems: "center", gap: 9, padding: "8px 11px", borderRadius: 7, background: item.active ? "#1e2030" : "transparent", cursor: "pointer", fontSize: 15, color: item.active ? "#e2e8f0" : "#475569" }}
              >
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                  <path d={item.icon} stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                {item.label}
              </div>
            </Link>
          ))}
        </div>

        <div style={{ marginTop: 24 }}>
          <div style={{ fontSize: 13, textTransform: "uppercase", letterSpacing: "0.1em", color: "#1e2030", marginBottom: 10 }}>Sectors</div>
          {Object.entries(SECTOR_STATS).map(([s, info]) => (
            <div
              key={s}
              onClick={() => setSector(sector === s ? "All" : s)}
              style={{ display: "flex", alignItems: "center", gap: 7, padding: "6px 0", cursor: "pointer" }}
            >
              <div style={{ width: 7, height: 7, borderRadius: "50%", background: info.color, flexShrink: 0 }} />
              <span style={{ fontSize: 14, color: sector === s ? "#e2e8f0" : "#475569" }}>{s}</span>
            </div>
          ))}
        </div>
      </aside>

      {/* ── Main ── */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

        {/* Header */}
        <header style={{ borderBottom: "1px solid #1e2030", padding: "16px 28px", display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
          <div>
            <h1 style={{ margin: 0, fontSize: 20, fontWeight: 600, letterSpacing: "-0.02em" }}>ESG Dashboard</h1>
            <p style={{ margin: 0, fontSize: 15, color: "#475569" }}>FY2023 · BRSR disclosures · {COMPANIES.length} companies</p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {/* Search */}
            <div style={{ display: "flex", alignItems: "center", gap: 7, background: "#0f1117", border: "1px solid #1e2030", borderRadius: 7, padding: "7px 12px" }}>
              <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><circle cx="7" cy="7" r="4" stroke="#475569" strokeWidth="1.5" /><path d="M10 10l3 3" stroke="#475569" strokeWidth="1.5" strokeLinecap="round" /></svg>
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search companies…"
                style={{ background: "none", border: "none", outline: "none", fontSize: 16, color: "#e2e8f0", width: 170, fontFamily: "inherit" }}
              />
            </div>

            {/* Compare button */}
            <Link href="/compare" style={{ textDecoration: "none" }}>
              <button style={{ display: "flex", alignItems: "center", gap: 7, padding: "8px 16px", background: "#1e2030", border: "1px solid #334155", borderRadius: 7, cursor: "pointer", fontSize: 16, fontWeight: 600, color: "#94a3b8", letterSpacing: "0.01em" }}>
                <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M2 8h5M9 8h5M8 2v5M8 9v5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
                Compare
              </button>
            </Link>

            {/* Research button */}
            <Link href="/research" style={{ textDecoration: "none" }}>
              <button style={{ display: "flex", alignItems: "center", gap: 7, padding: "8px 16px", background: "linear-gradient(135deg,#6366f1,#22d3ee)", border: "none", borderRadius: 7, cursor: "pointer", fontSize: 16, fontWeight: 600, color: "white", letterSpacing: "0.01em" }}>
                <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M2 12L6 4l4 6 2-3 2 5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
                Research with AI
              </button>
            </Link>
          </div>
        </header>

        {/* Sector overview strip */}
        <div style={{ borderBottom: "1px solid #1e2030", padding: "14px 28px", display: "flex", gap: 12, flexShrink: 0, overflowX: "auto" }}>
          {Object.entries(SECTOR_STATS).map(([s, info]) => (
            <div
              key={s}
              onClick={() => setSector(sector === s ? "All" : s)}
              style={{ flexShrink: 0, background: sector === s ? "#0f1117" : "transparent", border: `1px solid ${sector === s ? info.color : "#1e2030"}`, borderRadius: 8, padding: "10px 16px", cursor: "pointer", minWidth: 140, transition: "all 0.15s" }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 5 }}>
                <div style={{ width: 7, height: 7, borderRadius: "50%", background: info.color }} />
                <span style={{ fontSize: 14, color: info.color, fontWeight: 600 }}>{s}</span>
              </div>
              <div style={{ fontSize: 24, fontWeight: 700, color: "#e2e8f0", marginBottom: 2 }}>{info.avgScore}</div>
              <div style={{ fontSize: 13, color: "#334155" }}>avg ESG · {info.companies} co.</div>
            </div>
          ))}
        </div>

        {/* Filters row */}
        <div style={{ padding: "10px 28px", display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0, borderBottom: "1px solid #0f1117" }}>
          <div style={{ display: "flex", gap: 6 }}>
            {SECTORS.map((s) => (
              <button
                key={s}
                onClick={() => setSector(s)}
                style={{ fontSize: 15, padding: "5px 12px", borderRadius: 6, border: `1px solid ${sector === s ? "#6366f1" : "#1e2030"}`, background: sector === s ? "#1e1b4b" : "transparent", color: sector === s ? "#818cf8" : "#475569", cursor: "pointer", fontFamily: "inherit" }}
              >
                {s}
              </button>
            ))}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 15, color: "#334155" }}>Sort:</span>
            {(["score", "ghg", "renewable"] as const).map((s) => (
              <button
                key={s}
                onClick={() => setSort(s)}
                style={{ fontSize: 15, padding: "5px 12px", borderRadius: 6, border: `1px solid ${sort === s ? "#6366f1" : "#1e2030"}`, background: sort === s ? "#1e1b4b" : "transparent", color: sort === s ? "#818cf8" : "#475569", cursor: "pointer", fontFamily: "inherit" }}
              >
                {s === "score" ? "ESG Score" : s === "ghg" ? "Low GHG" : "Renewable"}
              </button>
            ))}
          </div>
        </div>

        {/* Cards grid */}
        <div style={{ flex: 1, overflowY: "auto", padding: "22px 28px" }}>
          {filtered.length === 0 ? (
            <div style={{ textAlign: "center", color: "#334155", paddingTop: 60, fontSize: 17 }}>No companies match your filter.</div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 14 }}>
              {filtered.map((company) => (
                <CompanyCard
                  key={company.id}
                  company={company}
                  selected={selected?.id === company.id}
                  onClick={() => setSelected(selected?.id === company.id ? null : company)}
                />
              ))}
            </div>
          )}
        </div>
      </main>

      {/* ── Detail panel ── */}
      <aside style={{ width: selected ? 330 : 0, borderLeft: selected ? "1px solid #1e2030" : "none", overflow: "hidden", transition: "width 0.25s ease", flexShrink: 0 }}>
        {selected && <DetailPanel company={selected} onClose={() => setSelected(null)} />}
      </aside>

      <style>{`
        * { box-sizing: border-box; }
        body { margin: 0; }
        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #1e2030; border-radius: 2px; }
      `}</style>
    </div>
  );
}
