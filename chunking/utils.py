"""
Shared utilities for all BRSR chunking strategies.

Provides:
  - Path constants
  - CSV loading with encoding fallback
  - Row-type classifiers (domain, narrative, scalar)
  - Text helpers (decamelize, parse_dimensions)
  - BRSR principle mapper
  - Q&A text formatters for scalar and narrative rows
  - JSONL writer
"""

from __future__ import annotations

import json
import re
import os
from pathlib import Path
from typing import Iterator

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parent.parent
CLEAN_DIR = ROOT_DIR / "brsr-data" / "clean"
CHUNKS_DIR = ROOT_DIR / "brsr-data" / "chunks"

# ---------------------------------------------------------------------------
# BRSR Principle mapping
# ---------------------------------------------------------------------------

PRINCIPLE_MAP: dict[str, str] = {
    "Principle1": "Principle 1: Business Ethics",
    "Principle2": "Principle 2: Sustainable Products",
    "Principle3": "Principle 3: Employee Wellbeing",
    "Principle4": "Principle 4: Stakeholder Engagement",
    "Principle5": "Principle 5: Human Rights",
    "Principle6": "Principle 6: Environment",
    "Principle7": "Principle 7: Policy Advocacy",
    "Principle8": "Principle 8: Inclusive Growth",
    "Principle9": "Principle 9: Consumer Responsibility",
}

# Keyword heuristics for elements that don't contain an explicit PrincipleN tag.
# Evaluated in order; first match wins.
_HEURISTIC_RULES: list[tuple[list[str], str]] = [
    # Principle 6 — Environment
    (
        ["Energy", "GhgEmission", "Emission", "WaterWithdrawal", "Water",
         "Waste", "Plastic", "Biodiversity", "LifeCycle", "Recycl",
         "Sustainabl", "Carbon", "Nitrogen"],
        "Principle 6: Environment",
    ),
    # Principle 3 — Employee Wellbeing
    (
        ["Employee", "Worker", "Turnover", "Diversity", "Gender", "Training",
         "Welfare", "Injury", "Fatality", "Health", "SafetyManagement",
         "Maternity", "Paternity", "Retirement", "Wage", "Salary"],
        "Principle 3: Employee Wellbeing",
    ),
    # Principle 9 — Consumer Responsibility
    (
        ["Consumer", "Customer", "Product", "ServiceQuality", "Complaint",
         "DataBreach", "Privacy", "CyberSecurity"],
        "Principle 9: Consumer Responsibility",
    ),
    # Principle 5 — Human Rights
    (
        ["HumanRights", "ChildLabour", "ForcedLabour", "Discrimination",
         "SexualHarassment", "Trafficking"],
        "Principle 5: Human Rights",
    ),
    # Principle 8 — Inclusive Growth
    (
        ["Csr", "CorporateSocialResponsibility", "Community", "SocialImpact",
         "Inclusive", "Rehabilitation", "Displacement"],
        "Principle 8: Inclusive Growth",
    ),
    # Principle 4 — Stakeholder Engagement
    (
        ["Stakeholder", "MaterialIssue", "Grievance", "Engagement"],
        "Principle 4: Stakeholder Engagement",
    ),
    # Principle 7 — Policy Advocacy
    (
        ["PolicyAdvocacy", "TradeAssociation", "PublicPolicy", "Lobbying"],
        "Principle 7: Policy Advocacy",
    ),
    # Principle 1 — Business Ethics
    (
        ["Ethics", "Corruption", "AntiCorruption", "Bribe", "Transparency",
         "Conflict", "Integrity", "Penalty", "Conviction"],
        "Principle 1: Business Ethics",
    ),
    # Principle 2 — Sustainable Products
    (
        ["SupplyChain", "Supplier", "LifecycleAssessment", "Sustainable",
         "Resource", "Recycle"],
        "Principle 2: Sustainable Products",
    ),
]


def map_principle(element: str) -> str:
    """Return the BRSR principle/section for a given XBRL element name."""
    # 1. Explicit PrincipleN in name
    for key, label in PRINCIPLE_MAP.items():
        if key in element:
            return label
    # 2. Keyword heuristics
    for keywords, label in _HEURISTIC_RULES:
        for kw in keywords:
            if kw.lower() in element.lower():
                return label
    # 3. Fallback
    return "Section A: General Disclosures"


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def decamelize(text: str) -> str:
    """Convert a camelCase XBRL element name to a spaced, readable label.

    e.g. 'NumberOfEmployeesOrWorkersIncludingDifferentlyAbled'
         -> 'Number Of Employees Or Workers Including Differently Abled'
    e.g. 'GhgEmissionsScope1' -> 'Ghg Emissions Scope 1'
    e.g. 'NotesPrinciple3ExplanatoryTextBlock' -> 'Notes Principle 3'
    """
    # Strip ExplanatoryTextBlock suffix first
    s = re.sub(r"ExplanatoryTextBlock$", "", text)
    # Insert space before uppercase letter preceded by a lowercase letter
    s = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)
    # Insert space before uppercase letter followed by lowercase (handles ABCDef -> ABC Def)
    s = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", s)
    # Insert space before a digit preceded by a letter
    s = re.sub(r"(?<=[a-zA-Z])(?=[0-9])", " ", s)
    # Insert space before a letter preceded by a digit
    s = re.sub(r"(?<=[0-9])(?=[a-zA-Z])", " ", s)
    return s.strip()


def parse_dimensions(dim_string: str) -> str:
    """Parse an XBRL dimensions string into human-readable key=value pairs.

    Input:  'in-capmkt:GenderAxis=in-capmkt:MaleMember; in-capmkt:LocationAxis=in-capmkt:OfficeMember'
    Output: 'Gender = Male | Location = Office'
    """
    if not dim_string or not dim_string.strip():
        return ""

    parts = []
    for pair in dim_string.split(";"):
        pair = pair.strip()
        if "=" not in pair:
            continue
        axis_raw, member_raw = pair.split("=", 1)

        # Strip namespace prefix
        axis = re.sub(r"^[^:]+:", "", axis_raw).strip()
        member = re.sub(r"^[^:]+:", "", member_raw).strip()

        # Strip 'Axis' suffix from key, 'Member' suffix from value
        axis = re.sub(r"Axis$", "", axis)
        member = re.sub(r"Member$", "", member)

        # Decamelize both
        axis = decamelize(axis)
        member = decamelize(member)

        if axis and member:
            parts.append(f"{axis} = {member}")

    return " | ".join(parts)


# ---------------------------------------------------------------------------
# Row-type classifiers
# ---------------------------------------------------------------------------

def is_domain_row(element: str) -> bool:
    """True for XBRL taxonomy domain/member placeholder rows (not real data)."""
    lower = element.lower()
    return lower.endswith("domain") or lower.endswith("member")


def is_narrative_row(element: str) -> bool:
    """True for free-text ExplanatoryTextBlock disclosures."""
    return "ExplanatoryTextBlock" in element


# ---------------------------------------------------------------------------
# Q&A text formatters
# ---------------------------------------------------------------------------

def scalar_row_to_text(row: dict) -> str:
    """Format a scalar (numeric/categorical) row as structured Q&A text."""
    company_header = (
        f"Company: {row['companyName']} ({row['symbol']}) | "
        f"FY: {row['fyFrom']}-{row['fyTo']}"
    )
    metric = decamelize(row["element"])
    context = parse_dimensions(str(row.get("dimensions", "") or ""))
    value = str(row["value"]).strip()
    unit = str(row.get("unit", "") or "").strip()
    period = str(row.get("period", "") or "").strip()

    value_line = f"Value: {value}"
    if unit and unit not in ("nan", ""):
        value_line += f" (unit: {unit})"

    lines = [company_header, f"Metric: {metric}"]
    if context:
        lines.append(f"Context: {context}")
    lines.append(value_line)
    if period and period not in ("nan", " to ", ""):
        lines.append(f"Period: {period}")
    return "\n".join(lines)


def narrative_row_to_text(row: dict) -> str:
    """Format a narrative ExplanatoryTextBlock row as a disclosure text."""
    company_header = (
        f"Company: {row['companyName']} ({row['symbol']}) | "
        f"FY: {row['fyFrom']}-{row['fyTo']}"
    )
    topic = decamelize(row["element"])
    disclosure = str(row["value"]).strip()
    period = str(row.get("period", "") or "").strip()

    lines = [company_header, f"Topic: {topic}", f"Disclosure: {disclosure}"]
    if period and period not in ("nan", " to ", ""):
        lines.append(f"Period: {period}")
    return "\n".join(lines)


def grouped_rows_to_text(
    rows: list[dict],
    company_name: str,
    symbol: str,
    fy_from: str,
    fy_to: str,
    section: str | None = None,
) -> str:
    """Format a group of rows as a multi-metric Q&A block."""
    header = f"Company: {company_name} ({symbol}) | FY: {fy_from}-{fy_to}"
    if section:
        header += f" | Section: {section}"

    lines = [header, ""]
    for row in rows:
        metric = decamelize(row["element"])
        context = parse_dimensions(str(row.get("dimensions", "") or ""))
        value = str(row["value"]).strip()
        unit = str(row.get("unit", "") or "").strip()

        label = metric
        if context:
            label += f" [{context}]"

        value_str = value
        if unit and unit not in ("nan", ""):
            value_str += f" ({unit})"

        lines.append(f"{label}: {value_str}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CSV loader
# ---------------------------------------------------------------------------

def load_company_df(filepath: Path | str) -> pd.DataFrame:
    """Load a clean company CSV with automatic encoding fallback."""
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            df = pd.read_csv(filepath, encoding=enc, dtype=str, low_memory=False)
            # Normalise NaN → empty string for string columns
            df = df.fillna("")
            return df
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not decode {filepath} with any tried encoding.")


def iter_clean_files() -> Iterator[tuple[Path, pd.DataFrame]]:
    """Yield (path, DataFrame) for every company CSV in CLEAN_DIR."""
    files = sorted(CLEAN_DIR.glob("*_clean.csv"))
    for fp in files:
        if fp.name == "quality_report.csv":
            continue
        yield fp, load_company_df(fp)


def filter_df(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split a company DataFrame into (scalar_df, narrative_df), dropping domain rows."""
    mask_domain = df["element"].apply(is_domain_row)
    mask_narrative = df["element"].apply(is_narrative_row)

    scalar_df = df[~mask_domain & ~mask_narrative].copy()
    narrative_df = df[mask_narrative].copy()
    return scalar_df, narrative_df


# ---------------------------------------------------------------------------
# JSONL writer
# ---------------------------------------------------------------------------

def write_jsonl(chunks: list[dict], out_dir: Path, filename: str = "chunks.jsonl") -> Path:
    """Write a list of chunk dicts to a JSONL file, creating out_dir if needed."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    with open(out_path, "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    return out_path
