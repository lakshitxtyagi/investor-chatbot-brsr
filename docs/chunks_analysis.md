# BRSR Chunking Strategy — Analysis Report

## Summary Table

| Strategy            |    Chunks | Mean Words | Median Words | p95 Words | Max Words | ~Mean Tokens |
| ------------------- | --------: | ---------: | -----------: | --------: | --------: | -----------: |
| S1: Row-level       | 2,114,353 |       38.7 |         36.0 |      51.0 |     2,931 |         51.6 |
| S2: N-row Window    |   705,355 |      129.6 |        123.0 |     205.0 |     6,884 |        172.8 |
| S3: Principle-based |    11,530 |    4,244.0 |      1,073.0 |  20,997.5 |    34,375 |      5,658.6 |
| S4: Type-aware      |   118,369 |      425.8 |         67.0 |     738.6 |    24,486 |        567.7 |
| S5: Company Summary |     1,227 |    3,918.5 |      3,847.0 |   4,401.0 |     5,370 |      5,224.7 |

> Token estimate uses the approximation: **1 token ≈ 0.75 words**.

---

## Strategy Notes

### S1: Row-level (Atomic)

- Highest granularity — one chunk per ESG indicator row.
- Very compact (~37 words average), well within any embedding model's context window.
- 2.1M chunks total — largest index to maintain.
- Risk: loses contextual coherence between related indicators.

### S2: N-row Sliding Window (N=5, overlap=2)

- Moderate granularity — groups 5 consecutive rows with a 2-row overlap.
- ~130 words average, compact and consistent.
- 705K chunks — good balance of index size and context.
- Risk: groupings are positional, not semantic.

### S3: Principle-based (Semantic)

- Lowest chunk count (11,530) — one chunk per (company × BRSR principle).
- Highly variable size: median ~1K words but p95 jumps to ~21K words.
- Mean of ~5,659 tokens likely exceeds context limits of many embedding models (typical limit: 512–8192 tokens).
- Best alignment with how analysts query BRSR data.
- Recommendation: consider splitting large principle chunks if using a 512-token embedding model.

### S4: Type-aware (Narrative + Numeric separate) -> PRIMARY CHUNKING STRATEGY

- Separates free-text disclosures (narrative) from numeric indicators.
- 118K chunks with a bimodal size distribution — narratives are long, numeric groups are short (median ~67 words).
- Addresses the heterogeneity problem: avoids diluting narrative embeddings with raw numbers.
```text
All rows in a company CSV
│
├── Domain rows (element ends in Domain/Member)  → DISCARDED (not chunked)
│
├── Narrative rows (element contains ExplanatoryTextBlock)  → BUCKET 1: Narrative track
│                                                              one chunk per row
│
└── Everything else (numeric, Yes/No, categorical,          → BUCKET 2: Scalar track
    short remarks like "-", booleans, percentages...)          grouped by principle,
                                                               one chunk per (company, principle)
```
- Narrative track → 1 row = 1 chunk Each ExplanatoryTextBlock row becomes its own independent chunk. One policy narrative = one chunk.
- Scalar track → 1 bucket = 1 chunk All scalar rows for a (company, principle) pair are grouped together into one chunk. So for example, all of ZFCVINDIA's Principle 3 numeric/categorical rows — employee counts, turnover rates, gender percentages, GrievanceRedressalMechanismInPlace: No, etc. — all go into one single chunk.

### S5: Company Summary -> SECONDARY CHUNKING STRATEGY

- One chunk per company — smallest index (1,227 chunks).
- Very dense (~3,919 words / ~5,225 tokens average) — may hit context limits for some embedding models.
- Best suited for high-level cross-company comparison queries.

---

## Chunk Size Distribution

![Chunk Analysis Histogram](docs/chunk_analysis.png)
