"""
due_diligence.py — Multi-section Due Diligence Report Agent
============================================================
Runs 10 targeted RAG queries against the BRSR Weaviate index (one per
report section), aggregates retrieved chunks, and generates a single
structured markdown report via Groq.

All analysis is grounded exclusively in the BRSR data stored in Weaviate.
The prompt forbids the model from using external knowledge.
"""

from __future__ import annotations

from groq import Groq

from config import settings
from rag import get_embedder, retrieve_chunks

# ---------------------------------------------------------------------------
# Token budget constants
# Numeric chunks are section-level buckets (avg 29k chars); naive truncation
# at 120 chars just cuts the header. We use keyword-based line extraction
# instead, capping at _MAX_EXTRACTED_LINES relevant lines per chunk.
# Total budget target: ~4,000 tokens input for Groq free tier.
# ---------------------------------------------------------------------------
_MAX_EXTRACTED_LINES = 20    # lines extracted per chunk for large chunks
_MAX_LINE_CHARS = 120        # characters kept per extracted line
_MAX_NARRATIVE_CHARS = 500   # chars kept for short narrative chunks
_MAX_CONTEXT_CHARS = 14_000  # hard cap on the full assembled context string

# Keywords per section used to extract relevant lines from large numeric chunks
_SECTION_KEYWORDS: dict[str, list[str]] = {
    "Company Profile & Operations": [
        "cin", "corporate identity", "name of the company", "date of incorporation",
        "registered office", "stock exchange", "nic code", "number of locations",
        "address", "business activity", "type of organisation",
    ],
    "Financial Overview": [
        "revenue", "turnover", "paid-up capital", "net worth", "export",
        "sales", "income from operations", "total income", "paid up",
    ],
    "Workforce & Diversity": [
        "total number of employee", "permanent employee", "contractual",
        "female", "male", "differently abled", "wages", "turnover rate",
        "worker", "headcount",
    ],
    "Health, Safety & Training": [
        "fatali", "injur", "lost time", "safety incident", "training",
        "health and safety", "near miss", "rehab",
    ],
    "Environmental — GHG & Energy": [
        "scope 1", "scope 2", "scope 3", "greenhouse gas", "ghg",
        "energy consumption", "renewable", "non-renewable", "energy intensity",
        "emission",
    ],
    "Environmental — Water & Waste": [
        "water withdrawal", "water consumption", "water discharge",
        "waste generated", "waste recycled", "waste disposed", "water intensity",
        "effluent",
    ],
    "Governance & Ethics": [
        "complaint", "penalt", "fine", "conviction", "anti-corruption",
        "board", "transparency", "whistle", "bribery",
    ],
    "Consumer Responsibility": [
        "consumer complaint", "data breach", "cybersecurity", "privacy",
        "product recall", "customer grievance", "cyber",
    ],
    "Stakeholder Engagement & CSR": [
        "csr", "community", "stakeholder", "grievance", "csr spend",
        "social impact", "inclusive",
    ],
    "Policy & Sustainability Disclosures": [
        "policy", "sustainability", "esg", "commitment", "certification",
        "standard", "framework", "disclosure",
    ],
}

# ---------------------------------------------------------------------------
# Report section definitions
# ---------------------------------------------------------------------------

REPORT_SECTIONS: list[dict] = [
    {
        "title": "Company Profile & Operations",
        "query_template": "Company identity CIN business activities locations {company}",
        "collections": ["NumericalCollection"],
        "top_k": 3,
    },
    {
        "title": "Financial Overview",
        "query_template": "Revenue turnover paid-up capital exports financial {company}",
        "collections": ["NumericalCollection"],
        "top_k": 3,
    },
    {
        "title": "Workforce & Diversity",
        "query_template": "Employees permanent contractual gender diversity wages {company}",
        "collections": ["NumericalCollection"],
        "top_k": 3,
    },
    {
        "title": "Health, Safety & Training",
        "query_template": "Fatalities injuries health safety training programs {company}",
        "collections": ["NumericalCollection"],
        "top_k": 3,
    },
    {
        "title": "Environmental — GHG & Energy",
        "query_template": "Scope 1 Scope 2 GHG emissions energy consumption renewable {company}",
        "collections": ["NumericalCollection"],
        "top_k": 3,
    },
    {
        "title": "Environmental — Water & Waste",
        "query_template": "Water withdrawal consumption waste generated recycled disposed {company}",
        "collections": ["NumericalCollection"],
        "top_k": 3,
    },
    {
        "title": "Governance & Ethics",
        "query_template": "Anti-corruption ethics board BRSR principle compliance policies {company}",
        "collections": ["NarrativeCollection", "NumericalCollection"],
        "top_k": 2,
    },
    {
        "title": "Consumer Responsibility",
        "query_template": "Consumer complaints data breaches cybersecurity privacy {company}",
        "collections": ["NumericalCollection"],
        "top_k": 3,
    },
    {
        "title": "Stakeholder Engagement & CSR",
        "query_template": "CSR community stakeholder grievance engagement {company}",
        "collections": ["NarrativeCollection"],
        "top_k": 2,
    },
    {
        "title": "Policy & Sustainability Disclosures",
        "query_template": "Sustainability ESG policy commitments responsibility {company}",
        "collections": ["NarrativeCollection"],
        "top_k": 2,
    },
]


# ---------------------------------------------------------------------------
# Context builder (per section)
# ---------------------------------------------------------------------------

def _extract_relevant_lines(text: str, section_title: str) -> str:
    """For large numeric section chunks, extract only lines matching section keywords."""
    keywords = _SECTION_KEYWORDS.get(section_title, [])

    all_lines = text.splitlines()
    # Always keep the header line (company / FY info)
    header = all_lines[0] if all_lines else ""

    scored: list[tuple[int, str]] = []
    for line in all_lines[1:]:
        lower = line.lower()
        score = sum(1 for kw in keywords if kw in lower)
        if score > 0:
            # Truncate individual long lines
            if len(line) > _MAX_LINE_CHARS:
                line = line[:_MAX_LINE_CHARS] + "…"
            scored.append((score, line))

    # Sort by relevance, take top lines
    scored.sort(key=lambda x: x[0], reverse=True)
    top_lines = [line for _, line in scored[:_MAX_EXTRACTED_LINES]]

    if not top_lines:
        # Fallback: just first few lines of the chunk
        fallback = "\n".join(all_lines[1:6])
        return f"{header}\n{fallback}"

    return f"{header}\n" + "\n".join(top_lines)


def _build_section_context(section_title: str, chunks: list[dict]) -> str:
    if not chunks:
        return f"[{section_title}]: no data retrieved"

    parts = [f"[{section_title}]"]
    for c in chunks:
        meta = c.get("metadata", {})
        useful = {k: v for k, v in meta.items()
                  if v and k in ("symbol", "companyName", "period", "row_type")}
        meta_str = ", ".join(f"{k}={v}" for k, v in useful.items())
        if meta_str:
            parts.append(meta_str)

        text = c["text"]
        row_type = meta.get("row_type", "")

        if row_type == "numeric" and len(text) > _MAX_NARRATIVE_CHARS:
            # Large numeric section buckets: extract relevant lines
            text = _extract_relevant_lines(text, section_title)
        elif len(text) > _MAX_NARRATIVE_CHARS:
            # Narrative chunks: plain truncation is fine
            text = text[:_MAX_NARRATIVE_CHARS] + "…"

        parts.append(text)

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Groq report generator
# ---------------------------------------------------------------------------

def _call_groq_report(company: str, section_contexts: list[str]) -> str:
    joined = "\n\n".join(section_contexts)

    # Hard cap to stay within token limits
    if len(joined) > _MAX_CONTEXT_CHARS:
        joined = joined[:_MAX_CONTEXT_CHARS] + "\n[context truncated]"

    prompt = (
        f"Company: {company}\n\n"
        "DATA (from BRSR filings only):\n"
        f"{joined}\n\n"
        "Write a Due Diligence Report in markdown covering: Executive Summary, "
        "Company Profile, Financial Overview, Workforce & Diversity, Health & Safety, "
        "Environmental (GHG/Energy/Water/Waste), Governance & Ethics, Consumer Responsibility, "
        "CSR & Stakeholders, Policy Disclosures, Key Risks. "
        "Use only the data above. State 'No data available' for missing sections."
    )

    client = Groq(api_key=settings.GROQ_API_KEY)
    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior ESG analyst. Use ONLY the BRSR data in the user message. "
                    "Do NOT use external knowledge. Output clean, structured markdown."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=2048,
    )
    return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def execute_due_diligence(
    company: str,
    symbol: str | None = None,
) -> dict:
    """Run the multi-section due diligence agent.

    Args:
        company: Company name or ticker as typed by the user.
        symbol: Optional exact NSE symbol to scope Weaviate queries to one company.

    Returns:
        { company, symbol, report_markdown, sections: [{title, chunk_count, sources}], total_sources }
    """
    embedder = get_embedder()
    all_sources: list[dict] = []
    section_contexts: list[str] = []
    sections_meta: list[dict] = []

    for section in REPORT_SECTIONS:
        query = section["query_template"].format(company=company)
        query_vector: list[float] = embedder.encode(query).tolist()

        section_chunks: list[dict] = []
        for col in section["collections"]:
            chunks = retrieve_chunks(
                query_vector=query_vector,
                collection_name=col,
                top_k=section["top_k"],
                symbol=symbol,
            )
            section_chunks.extend(chunks)

        # Deduplicate within section and sort by score
        seen: set[str] = set()
        unique_chunks: list[dict] = []
        for c in section_chunks:
            if c["chunk_id"] not in seen:
                seen.add(c["chunk_id"])
                unique_chunks.append(c)
        unique_chunks.sort(key=lambda x: x["score"], reverse=True)

        section_contexts.append(_build_section_context(section["title"], unique_chunks))
        sections_meta.append(
            {
                "title": section["title"],
                "chunk_count": len(unique_chunks),
                "sources": unique_chunks,
            }
        )
        all_sources.extend(unique_chunks)

    # Global deduplication of sources
    seen_global: set[str] = set()
    deduped_sources: list[dict] = []
    for c in all_sources:
        if c["chunk_id"] not in seen_global:
            seen_global.add(c["chunk_id"])
            deduped_sources.append(c)

    report_markdown = _call_groq_report(company, section_contexts)

    return {
        "company": company,
        "symbol": symbol,
        "report_markdown": report_markdown,
        "sections": sections_meta,
        "total_sources": len(deduped_sources),
    }
