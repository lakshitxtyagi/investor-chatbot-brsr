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
# Groq free tier: ~6k tokens/min for llama-3.1-8b-instant.
# Target: keep total prompt under ~3,500 tokens.
# At ~4 chars/token: 10 sections × 3 chunks × 120 chars ≈ 3,600 chars ≈ 900 tokens context
# + prompt template ≈ 400 tokens → ~1,300 tokens input, ~1,500 tokens output = ~2,800 total.
# ---------------------------------------------------------------------------
_MAX_CHUNK_CHARS = 120    # characters kept per chunk in the prompt
_MAX_CONTEXT_CHARS = 8_000  # hard cap on the full assembled context string

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

def _build_section_context(section_title: str, chunks: list[dict]) -> str:
    if not chunks:
        return f"[{section_title}]: no data"

    lines = [f"[{section_title}]"]
    for c in chunks:
        meta = c.get("metadata", {})
        # Only keep the most useful metadata fields
        useful = {k: v for k, v in meta.items()
                  if v and k in ("symbol", "companyName", "period", "element", "chunk_type")}
        if useful:
            lines.append(", ".join(f"{k}={v}" for k, v in useful.items()))
        text = c["text"]
        if len(text) > _MAX_CHUNK_CHARS:
            text = text[:_MAX_CHUNK_CHARS] + "…"
        lines.append(text)
    return "\n".join(lines)


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
