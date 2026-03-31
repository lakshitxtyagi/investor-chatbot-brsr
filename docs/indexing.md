content = """# 📦 ESG RAG Indexing Strategy (Weaviate + Type-Aware Chunking)

---

# 🚀 Overview

This document defines the **final indexing strategy** for ESG datasets using:

- Type-aware chunking (Narrative + Numerical separation)
- Weaviate as the vector database
- Dockerized deployment
- Metadata-driven filtering

---

# 🧠 Chunk Types

We define **two distinct chunk types**:

## 1. Narrative Chunks
- Derived from: `ExplanatoryTextBlock`
- Nature: Long-form text
- Purpose: Semantic understanding

## 2. Numerical (Scalar) Chunks
- Derived from:
  - Numbers
  - Percentages
  - Yes/No
  - Categorical values
- Purpose: Fact-based retrieval

---

# 🏗️ Collection Strategy (Weaviate)

We use:

## ✅ Single Cluster
Inside the cluster:

### 1. `NarrativeCollection`
- Stores all narrative chunks

### 2. `NumericalCollection`
- Stores all scalar/numerical chunks

👉 Separation ensures:
- Clean embeddings
- Better retrieval accuracy
- No mixing of text + numbers

---

# 🧾 Chunk Structure

## Example Narrative Chunk

```json
{
  "chunk_id": "s4_ABSLAMC_2024_2025_narr0028",
  "text": "Company: Aditya Birla Sun Life AMC Limited (ABSLAMC) | FY: 2024-2025 ...",
  "metadata": {
    "strategy": "strategy4_type_aware",
    "row_type": "narrative",
    "symbol": "ABSLAMC",
    "companyName": "Aditya Birla Sun Life AMC Limited",
    "fyFrom": "2024",
    "fyTo": "2025",
    "element": "SpecificCommitmentsGoalsAndTargetsSetByTheEntityWithDefinedTimelinesExplanatoryTextBlock",
    "principle": "Section A: General Disclosures",
    "period": "2024-04-01 to 2025-03-31",
    "source_file": "ABSLAMC_2024_2025_clean.csv"
  }
}
