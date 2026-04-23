"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";

// ─── Types ───────────────────────────────────────────────────────────────────

type Company = {
  id: string;
  name: string;
  ticker: string;
  sector: string;
  score: number;
  grade: string;
  ghg: number;
  water: number;
  energy: number;
  waste: number;
  renewableShare: number;
  trend: string;
  fy: string;
  principles: { compliant: number; partial: number; violated: number };
  highlights: string[];
  envScore: number;
  socialScore: number;
  govScore: number;
  overallTos: number;
  srs: number;
};

type SectorInfo = { avgScore: number; avgGhg: number; color: string; companies: number };

// ─── Sector color palette ─────────────────────────────────────────────────────

const SECTOR_COLORS: Record<string, string> = {
  "Information, Communication & Technology": "#6366f1",
  "Financial Services": "#22d3ee",
  "Mining and Metals": "#f59e0b",
  "Oil, Gas & Consumable Fuels": "#ef4444",
  "Power Generation and Transmission": "#f87171",
  "Healthcare": "#a78bfa",
  "Chemicals": "#fb923c",
  "FMCG": "#22c55e",
  "Transportation and Automotive": "#38bdf8",
  "Apparel, Garments and Textiles": "#e879f9",
  "Real Estate & Construction": "#fbbf24",
  "Infrastructure and Construction": "#fcd34d",
  "Retail": "#4ade80",
  "Media and Entertainment": "#f472b6",
  "Services": "#818cf8",
  "Consumer Durables": "#34d399",
  "Industrial Products and Equipment": "#60a5fa",
  "Forestry and Forest Products": "#86efac",
  "Breweries, Distilleries and Beverages": "#fdba74",
  "Leisure and Recreation Services": "#c4b5fd",
  "Telecom": "#67e8f9",
  "Unclassified": "#475569",
};

function sectorColor(sector: string) {
  return SECTOR_COLORS[sector] ?? "#64748b";
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function GradeChip({ grade }: { grade: string }) {
  const colors: Record<string, { bg: string; color: string }> = {
    "A+": { bg: "#052e16", color: "#4ade80" },
    "A":  { bg: "#052e16", color: "#86efac" },
    "A-": { bg: "#052e16", color: "#bbf7d0" },
    "B+": { bg: "#1e293b", color: "#93c5fd" },
    "B":  { bg: "#1e293b", color: "#bfdbfe" },
    "B-": { bg: "#2d1b00", color: "#fbbf24" },
    "C":  { bg: "#2d0a0a", color: "#f87171" },
  };
  const c = colors[grade] ?? { bg: "#1e2030", color: "#94a3b8" };
  return (
    <span style={{ fontSize: 14, fontWeight: 700, padding: "3px 9px", borderRadius: 5, background: c.bg, color: c.color, letterSpacing: "0.04em" }}>
      {grade}
    </span>
  );
}

function TrendIcon({ trend }: { trend: string }) {
  if (trend === "up")   return <svg width="13" height="13" viewBox="0 0 12 12" fill="none"><path d="M2 9L6 3l4 6" stroke="#22c55e" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>;
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

// Skeleton card shown while loading
function SkeletonCard() {
  return (
    <div style={{ background: "#0a0a0f", border: "1px solid #1e2030", borderRadius: 10, padding: "18px" }}>
      <style>{`@keyframes pulse{0%,100%{opacity:.4}50%{opacity:.8}}`}</style>
      {[80, 120, 40, 60, 100].map((w, i) => (
        <div key={i} style={{ height: i === 0 ? 16 : 12, width: `${w}%`, background: "#1e2030", borderRadius: 4, marginBottom: 10, animation: "pulse 1.5s ease infinite" }} />
      ))}
    </div>
  );
}

function CompanyCard({ company, onClick, selected, sectorStats }: {
  company: Company;
  onClick: () => void;
  selected: boolean;
  sectorStats: Record<string, SectorInfo>;
}) {
  const sc = sectorStats[company.sector]?.color ?? sectorColor(company.sector);
  return (
    <div
      onClick={onClick}
      style={{ background: selected ? "#0f1117" : "#0a0a0f", border: `1px solid ${selected ? "#6366f1" : "#1e2030"}`, borderRadius: 10, padding: "18px", cursor: "pointer", transition: "all 0.15s ease", position: "relative", overflow: "hidden" }}
      onMouseEnter={(e) => { if (!selected) e.currentTarget.style.borderColor = "#334155"; }}
      onMouseLeave={(e) => { if (!selected) e.currentTarget.style.borderColor = "#1e2030"; }}
    >
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
          <span style={{ fontSize: 13, color: sc, background: `${sc}18`, padding: "2px 7px", borderRadius: 4, maxWidth: 110, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{company.sector}</span>
        </div>
      </div>

      <div style={{ marginBottom: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
          <span style={{ fontSize: 13, color: "#475569", textTransform: "uppercase", letterSpacing: "0.08em" }}>ESG Score</span>
          <span style={{ fontSize: 16, fontWeight: 600, color: "#e2e8f0" }}>{company.score}</span>
        </div>
        <ScoreBar value={company.score} color={sc} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
        {[
          { label: "GHG",   value: company.ghg,            unit: "Mt"  },
          { label: "Water", value: company.water,           unit: "Mm³" },
          { label: "Renew.", value: company.renewableShare, unit: "%"   },
        ].map((m) => (
          <div key={m.label} style={{ background: "#060608", border: "1px solid #1a1a2e", borderRadius: 6, padding: "7px 9px" }}>
            <div style={{ fontSize: 12, color: "#334155", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 3 }}>{m.label}</div>
            <div style={{ fontSize: 15, fontWeight: 600, color: "#94a3b8" }}>{m.value}<span style={{ fontSize: 12, color: "#334155", marginLeft: 2 }}>{m.unit}</span></div>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
        <span style={{ fontSize: 14, color: "#4ade80" }}>✓ {company.principles.compliant}</span>
        <span style={{ fontSize: 14, color: "#f59e0b" }}>~ {company.principles.partial}</span>
        <span style={{ fontSize: 14, color: "#ef4444" }}>✕ {company.principles.violated}</span>
        <span style={{ fontSize: 14, color: "#334155" }}>BRSR principles</span>
      </div>
    </div>
  );
}

function DetailPanel({ company, onClose, sectorStats }: {
  company: Company;
  onClose: () => void;
  sectorStats: Record<string, SectorInfo>;
}) {
  const sc = sectorStats[company.sector]?.color ?? sectorColor(company.sector);
  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
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
          <div style={{ fontSize: 56, fontWeight: 800, color: sc, lineHeight: 1, marginBottom: 5 }}>{company.score}</div>
          <div style={{ fontSize: 14, color: "#475569", textTransform: "uppercase", letterSpacing: "0.1em" }}>ESG Score / 100</div>
          <div style={{ marginTop: 14 }}><ScoreBar value={company.score} color={sc} /></div>
        </div>

        {/* ESG sub-scores */}
        <div style={{ fontSize: 14, textTransform: "uppercase", letterSpacing: "0.1em", color: "#334155", marginBottom: 10 }}>ESG Sub-Scores</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, marginBottom: 18 }}>
          {[
            { label: "Environmental", value: company.envScore, color: "#22c55e" },
            { label: "Social (TOS)", value: company.socialScore, color: "#6366f1" },
            { label: "Governance", value: company.govScore, color: "#22d3ee" },
          ].map((s) => (
            <div key={s.label} style={{ background: "#060608", border: "1px solid #1a1a2e", borderRadius: 8, padding: "11px 13px", textAlign: "center" }}>
              <div style={{ fontSize: 22, fontWeight: 700, color: s.color, marginBottom: 4 }}>{s.value.toFixed(0)}</div>
              <div style={{ fontSize: 12, color: "#334155", textTransform: "uppercase", letterSpacing: "0.06em" }}>{s.label}</div>
            </div>
          ))}
        </div>

        {/* Key Metrics */}
        <div style={{ fontSize: 14, textTransform: "uppercase", letterSpacing: "0.1em", color: "#334155", marginBottom: 10 }}>Key Metrics</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 18 }}>
          {[
            { label: "GHG Emissions",   value: `${company.ghg} Mt CO₂e`,         sub: "Scope 1+2" },
            { label: "Water Withdrawn", value: `${company.water} Mm³`,            sub: "Total" },
            { label: "Energy Used",     value: `${company.energy} PJ`,            sub: "Total" },
            { label: "Waste Generated", value: `${company.waste} kt`,             sub: "Total" },
            { label: "Renewable Mix",   value: `${company.renewableShare}%`,      sub: "Of total energy" },
            { label: "Trend",           value: company.trend === "up" ? "↑ Improving" : company.trend === "down" ? "↓ Declining" : "→ Stable", sub: "YoY" },
          ].map((m) => (
            <div key={m.label} style={{ background: "#060608", border: "1px solid #1a1a2e", borderRadius: 8, padding: "11px 13px" }}>
              <div style={{ fontSize: 12, color: "#334155", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 5 }}>{m.label}</div>
              <div style={{ fontSize: 17, fontWeight: 600, color: "#e2e8f0", marginBottom: 3 }}>{m.value}</div>
              <div style={{ fontSize: 13, color: "#334155" }}>{m.sub}</div>
            </div>
          ))}
        </div>

        {/* Social Risk Score */}
        <div style={{ background: "#0f1117", border: "1px solid #1e2030", borderRadius: 10, padding: "14px 18px", marginBottom: 18 }}>
          <div style={{ fontSize: 13, color: "#334155", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>Social Risk Score (SRS)</div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: company.srs < 25 ? "#22c55e" : company.srs < 50 ? "#86efac" : company.srs < 75 ? "#f59e0b" : "#ef4444" }}>
              {company.srs.toFixed(1)}
            </div>
            <div style={{ fontSize: 14, color: "#475569", textAlign: "right" }}>
              <div>{company.srs < 25 ? "Low Risk" : company.srs < 50 ? "Medium Risk" : company.srs < 75 ? "High Risk" : "Critical Risk"}</div>
              <div style={{ fontSize: 12, marginTop: 2 }}>TOS: {company.overallTos.toFixed(3)}</div>
            </div>
          </div>
          <div style={{ marginTop: 10 }}>
            <ScoreBar value={100 - company.srs} color={company.srs < 25 ? "#22c55e" : company.srs < 50 ? "#86efac" : company.srs < 75 ? "#f59e0b" : "#ef4444"} />
          </div>
        </div>

        {/* BRSR Principles */}
        <div style={{ fontSize: 14, textTransform: "uppercase", letterSpacing: "0.1em", color: "#334155", marginBottom: 10 }}>BRSR Compliance (9 Principles)</div>
        <div style={{ background: "#0f1117", border: "1px solid #1e2030", borderRadius: 10, padding: "16px 18px", marginBottom: 18 }}>
          <div style={{ display: "flex", gap: 20, marginBottom: 12 }}>
            {[
              { label: "Compliant", value: company.principles.compliant, color: "#4ade80" },
              { label: "Partial",   value: company.principles.partial,   color: "#f59e0b" },
              { label: "Violated",  value: company.principles.violated,  color: "#ef4444" },
            ].map((p) => (
              <div key={p.label} style={{ textAlign: "center" }}>
                <div style={{ fontSize: 28, fontWeight: 700, color: p.color }}>{p.value}</div>
                <div style={{ fontSize: 13, color: "#475569" }}>{p.label}</div>
              </div>
            ))}
          </div>
          <div style={{ display: "flex", gap: 2 }}>
            {Array.from({ length: 9 }).map((_, i) => {
              const isCompliant = i < company.principles.compliant;
              const isPartial   = i < company.principles.compliant + company.principles.partial;
              return <div key={i} style={{ flex: 1, height: 6, borderRadius: 2, background: isCompliant ? "#22c55e" : isPartial ? "#f59e0b" : "#ef4444" }} />;
            })}
          </div>
        </div>

        {/* Highlights */}
        <div style={{ fontSize: 14, textTransform: "uppercase", letterSpacing: "0.1em", color: "#334155", marginBottom: 10 }}>ESG Highlights</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 7, marginBottom: 26 }}>
          {company.highlights.map((h) => (
            <div key={h} style={{ display: "flex", alignItems: "center", gap: 9, background: "#0f1117", border: "1px solid #1e2030", borderRadius: 7, padding: "10px 13px" }}>
              <div style={{ width: 5, height: 5, borderRadius: "50%", background: sc, flexShrink: 0 }} />
              <span style={{ fontSize: 15, color: "#94a3b8" }}>{h}</span>
            </div>
          ))}
        </div>

        {/* CTAs */}
        <div style={{ display: "flex", gap: 8 }}>
          <Link href={`/compare?c1=${company.ticker}`} style={{ textDecoration: "none", flex: 1 }}>
            <button style={{ width: "100%", padding: "11px", background: "#1e2030", border: "1px solid #334155", borderRadius: 9, cursor: "pointer", fontSize: 15, fontWeight: 600, color: "#94a3b8" }}>
              Compare ↗
            </button>
          </Link>
          <Link href="/research" style={{ textDecoration: "none", flex: 1 }}>
            <button style={{ width: "100%", padding: "11px", background: "linear-gradient(135deg,#6366f1,#22d3ee)", border: "none", borderRadius: 9, cursor: "pointer", fontSize: 15, fontWeight: 600, color: "white" }}>
              Research with AI →
            </button>
          </Link>
        </div>
      </div>
    </div>
  );
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState<string | null>(null);
  const [sector, setSector]       = useState("All");
  const [sort, setSort]           = useState<"score" | "ghg" | "renewable">("score");
  const [selected, setSelected]   = useState<Company | null>(null);
  const [search, setSearch]       = useState("");
  const [showAll, setShowAll]     = useState(false);

  useEffect(() => {
    fetch("http://localhost:8000/companies?limit=500")
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then((data: Company[]) => { setCompanies(data); setLoading(false); })
      .catch((e) => { setError(String(e)); setLoading(false); });
  }, []);

  // Derive sector stats from live data
  const sectorStats = useMemo<Record<string, SectorInfo>>(() => {
    const groups: Record<string, Company[]> = {};
    companies.forEach((c) => {
      if (!groups[c.sector]) groups[c.sector] = [];
      groups[c.sector].push(c);
    });
    const out: Record<string, SectorInfo> = {};
    Object.entries(groups).forEach(([s, cs]) => {
      const avgScore = Math.round(cs.reduce((a, c) => a + c.score, 0) / cs.length);
      const avgGhg   = +(cs.reduce((a, c) => a + c.ghg, 0) / cs.length).toFixed(1);
      out[s] = { avgScore, avgGhg, color: sectorColor(s), companies: cs.length };
    });
    return out;
  }, [companies]);

  // Top sectors by company count for sidebar + strip
  const topSectors = useMemo(
    () => Object.entries(sectorStats)
      .filter(([s]) => s !== "Unclassified")
      .sort((a, b) => b[1].companies - a[1].companies)
      .slice(0, 10)
      .map(([s]) => s),
    [sectorStats]
  );

  const filtered = useMemo(() => {
    let arr = companies;
    if (sector !== "All") arr = arr.filter((c) => c.sector === sector);
    if (search)           arr = arr.filter((c) =>
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.ticker.toLowerCase().includes(search.toLowerCase())
    );
    const sorted = [...arr].sort((a, b) => {
      if (sort === "score")     return b.score - a.score;
      if (sort === "ghg")       return a.ghg - b.ghg;
      if (sort === "renewable") return b.renewableShare - a.renewableShare;
      return 0;
    });
    return sorted;
  }, [companies, sector, search, sort]);

  const visibleCount = showAll ? filtered.length : Math.min(filtered.length, 100);

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
            { label: "Dashboard", icon: "M2 12L6 4l4 6 2-3 2 5", active: true,  href: "/" },
            { label: "Compare",   icon: "M2 8h5M9 8h5M8 2v5M8 9v5", active: false, href: "/compare" },
            { label: "Research",  icon: "M3 3h10v10H3zM3 7h10M7 3v10", active: false, href: "/research" },
            { label: "Alerts",    icon: "M8 2a5 5 0 010 10A5 5 0 018 2zM8 14v1", active: false, href: "#" },
          ].map((item) => (
            <Link key={item.label} href={item.href} style={{ textDecoration: "none" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 9, padding: "8px 11px", borderRadius: 7, background: item.active ? "#1e2030" : "transparent", cursor: "pointer", fontSize: 15, color: item.active ? "#e2e8f0" : "#475569" }}>
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                  <path d={item.icon} stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                {item.label}
              </div>
            </Link>
          ))}
        </div>

        {/* Sector list */}
        <div style={{ marginTop: 24, overflowY: "auto" }}>
          <div style={{ fontSize: 13, textTransform: "uppercase", letterSpacing: "0.1em", color: "#1e2030", marginBottom: 10 }}>Top Sectors</div>
          <div
            onClick={() => setSector("All")}
            style={{ display: "flex", alignItems: "center", gap: 7, padding: "6px 0", cursor: "pointer" }}
          >
            <div style={{ width: 7, height: 7, borderRadius: "50%", background: "#6366f1", flexShrink: 0 }} />
            <span style={{ fontSize: 14, color: sector === "All" ? "#e2e8f0" : "#475569" }}>All</span>
          </div>
          {topSectors.map((s) => (
            <div
              key={s}
              onClick={() => setSector(sector === s ? "All" : s)}
              style={{ display: "flex", alignItems: "center", gap: 7, padding: "6px 0", cursor: "pointer" }}
            >
              <div style={{ width: 7, height: 7, borderRadius: "50%", background: sectorStats[s]?.color ?? "#64748b", flexShrink: 0 }} />
              <span style={{ fontSize: 13, color: sector === s ? "#e2e8f0" : "#475569", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s}</span>
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
            <p style={{ margin: 0, fontSize: 15, color: "#475569" }}>
              {loading ? "Loading BRSR data…" : `FY2025 · BRSR disclosures · ${companies.length.toLocaleString()} companies`}
            </p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 7, background: "#0f1117", border: "1px solid #1e2030", borderRadius: 7, padding: "7px 12px" }}>
              <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><circle cx="7" cy="7" r="4" stroke="#475569" strokeWidth="1.5" /><path d="M10 10l3 3" stroke="#475569" strokeWidth="1.5" strokeLinecap="round" /></svg>
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search companies…"
                style={{ background: "none", border: "none", outline: "none", fontSize: 16, color: "#e2e8f0", width: 170, fontFamily: "inherit" }}
              />
            </div>
            <Link href="/compare" style={{ textDecoration: "none" }}>
              <button style={{ display: "flex", alignItems: "center", gap: 7, padding: "8px 16px", background: "#1e2030", border: "1px solid #334155", borderRadius: 7, cursor: "pointer", fontSize: 16, fontWeight: 600, color: "#94a3b8" }}>
                <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M2 8h5M9 8h5M8 2v5M8 9v5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
                Compare
              </button>
            </Link>
            <Link href="/research" style={{ textDecoration: "none" }}>
              <button style={{ display: "flex", alignItems: "center", gap: 7, padding: "8px 16px", background: "linear-gradient(135deg,#6366f1,#22d3ee)", border: "none", borderRadius: 7, cursor: "pointer", fontSize: 16, fontWeight: 600, color: "white" }}>
                <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M2 12L6 4l4 6 2-3 2 5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
                Research with AI
              </button>
            </Link>
          </div>
        </header>

        {/* Sector overview strip */}
        <div style={{ borderBottom: "1px solid #1e2030", padding: "14px 28px", display: "flex", gap: 12, flexShrink: 0, overflowX: "auto" }}>
          {loading
            ? Array.from({ length: 5 }).map((_, i) => (
                <div key={i} style={{ flexShrink: 0, width: 140, height: 72, background: "#1e2030", borderRadius: 8, animation: "pulse 1.5s ease infinite" }} />
              ))
            : topSectors.map((s) => {
                const info = sectorStats[s];
                return (
                  <div
                    key={s}
                    onClick={() => setSector(sector === s ? "All" : s)}
                    style={{ flexShrink: 0, background: sector === s ? "#0f1117" : "transparent", border: `1px solid ${sector === s ? info.color : "#1e2030"}`, borderRadius: 8, padding: "10px 16px", cursor: "pointer", minWidth: 140, transition: "all 0.15s" }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 5 }}>
                      <div style={{ width: 7, height: 7, borderRadius: "50%", background: info.color }} />
                      <span style={{ fontSize: 13, color: info.color, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 110 }}>{s}</span>
                    </div>
                    <div style={{ fontSize: 24, fontWeight: 700, color: "#e2e8f0", marginBottom: 2 }}>{info.avgScore}</div>
                    <div style={{ fontSize: 13, color: "#334155" }}>avg ESG · {info.companies} co.</div>
                  </div>
                );
              })
          }
        </div>

        {/* Filters row */}
        <div style={{ padding: "10px 28px", display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0, borderBottom: "1px solid #0f1117" }}>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {(["All", ...topSectors]).map((s) => (
              <button
                key={s}
                onClick={() => setSector(s)}
                style={{ fontSize: 14, padding: "5px 12px", borderRadius: 6, border: `1px solid ${sector === s ? "#6366f1" : "#1e2030"}`, background: sector === s ? "#1e1b4b" : "transparent", color: sector === s ? "#818cf8" : "#475569", cursor: "pointer", fontFamily: "inherit", maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
              >
                {s}
              </button>
            ))}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
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
          {error && (
            <div style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 10, padding: "16px 20px", color: "#fca5a5", marginBottom: 20, fontSize: 15 }}>
              ⚠ Could not load company data: {error}
              <div style={{ fontSize: 13, marginTop: 6, color: "#94a3b8" }}>Make sure the backend is running on localhost:8000</div>
            </div>
          )}

          {loading ? (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 14 }}>
              {Array.from({ length: 12 }).map((_, i) => <SkeletonCard key={i} />)}
            </div>
          ) : filtered.length === 0 ? (
            <div style={{ textAlign: "center", color: "#334155", paddingTop: 60, fontSize: 17 }}>
              No companies match your filter.
            </div>
          ) : (
            <>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 14 }}>
                {filtered.slice(0, visibleCount).map((company) => (
                  <CompanyCard
                    key={company.id}
                    company={company}
                    selected={selected?.id === company.id}
                    onClick={() => setSelected(selected?.id === company.id ? null : company)}
                    sectorStats={sectorStats}
                  />
                ))}
              </div>
              {filtered.length > 100 && !showAll && (
                <div style={{ textAlign: "center", marginTop: 24 }}>
                  <div style={{ fontSize: 14, color: "#475569", marginBottom: 10 }}>
                    Showing {visibleCount} of {filtered.length} companies
                  </div>
                  <button
                    onClick={() => setShowAll(true)}
                    style={{ padding: "10px 28px", background: "#1e2030", border: "1px solid #334155", borderRadius: 8, color: "#94a3b8", fontSize: 15, fontWeight: 600, cursor: "pointer" }}
                  >
                    Load all {filtered.length} companies
                  </button>
                </div>
              )}
              {(showAll || filtered.length <= 100) && (
                <div style={{ textAlign: "center", marginTop: 16, fontSize: 14, color: "#334155" }}>
                  {filtered.length} companies · sorted by {sort === "score" ? "ESG Score" : sort === "ghg" ? "Low GHG" : "Renewable %"}
                </div>
              )}
            </>
          )}
        </div>
      </main>

      {/* ── Detail panel ── */}
      <aside style={{ width: selected ? 340 : 0, borderLeft: selected ? "1px solid #1e2030" : "none", overflow: "hidden", transition: "width 0.25s ease", flexShrink: 0 }}>
        {selected && <DetailPanel company={selected} onClose={() => setSelected(null)} sectorStats={sectorStats} />}
      </aside>

      <style>{`
        @keyframes pulse { 0%,100%{opacity:.4} 50%{opacity:.8} }
        * { box-sizing: border-box; }
        body { margin: 0; }
        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #1e2030; border-radius: 2px; }
      `}</style>
    </div>
  );
}
