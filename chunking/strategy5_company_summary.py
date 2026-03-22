"""
Strategy 5 — Company-level ESG Summary Chunking
================================================
Produces one compact summary chunk per (company, fiscal year) capturing
the most investor-relevant ESG KPIs across five categories:

  1. Company Identity & Operations
  2. Workforce & Social
  3. Environment (Energy / GHG / Water / Waste)
  4. Consumer Responsibility
  5. Governance & Ethics

This is ideal for cross-company comparison queries like:
"Compare GHG emissions of TCS and Infosys" or
"Which IT sector companies have the highest female employee ratio?"

Output: brsr-data/chunks/strategy5_company_summary/chunks.jsonl

Usage:
    python -m chunking.strategy5_company_summary
    python -m chunking.strategy5_company_summary --limit 10
"""

from __future__ import annotations

import argparse
from pathlib import Path

from tqdm import tqdm

from utils import (
    CHUNKS_DIR,
    decamelize,
    filter_df,
    iter_clean_files,
    parse_dimensions,
    write_jsonl,
)

STRATEGY = "strategy5_company_summary"
OUT_DIR = CHUNKS_DIR / STRATEGY

# ---------------------------------------------------------------------------
# KPI element groups: (section_label, [element_name_substrings])
# A row is included in a section if its element contains ANY of the substrings.
# ---------------------------------------------------------------------------
KPI_GROUPS: list[tuple[str, list[str]]] = [
    (
        "Company Identity & Operations",
        [
            "CorporateIdentityNumber",
            "NameOfTheCompany",
            "ValueOfSharesPaidUp",
            "NumberOfLocations",
            "NumberOfStatesWhereMarketServed",
            "NumberOfCountriesWhereMarketServed",
            "PercentageOfContributionOfExports",
            "DescriptionOfMainActivity",
            "DescriptionOfBusinessActivity",
        ],
    ),
    (
        "Workforce & Social",
        [
            "NumberOfEmployeesOrWorkersIncludingDifferentlyAbled",
            "PercentageOfEmployeesOrWorkersIncludingDifferentlyAbled",
            "TurnoverRate",
            "GrossWagesPaidToFemale",
            "TotalWagesPaid",
            "PercentageOfGrossWagesPaidToFemale",
            "NumberOfComplaintsFiledDuringTheYear",
            "NumberOfComplaintsPendingResolutionAtTheEndOfYear",
        ],
    ),
    (
        "Environment — Energy",
        [
            "TotalEnergyConsumedFromRenewableSources",
            "TotalEnergyConsumedFromNonRenewableSources",
            "TotalEnergyConsumedFromRenewableAndNonRenewableSources",
            "EnergyIntensityPerRupeeOfTurnover",
            "EnergyIntensityInTermOfPhysicalOutput",
        ],
    ),
    (
        "Environment — GHG Emissions",
        [
            "TotalScope1Emissions",
            "TotalScope2Emissions",
            "TotalScope3Emissions",
            "TotalScope1AndScope2EmissionsIntensityPerRupeeOfTurnover",
            "TotalScope1AndScope2EmissionsIntensityInTermOfPhysicalOutput",
        ],
    ),
    (
        "Environment — Water & Waste",
        [
            "TotalVolumeOfWaterWithdrawal",
            "TotalVolumeOfWaterConsumption",
            "WaterIntensityPerRupeeOfTurnover",
            "TotalWaterDischargedInKilolitres",
            "TotalWasteGenerated",
            "TotalWasteRecovered",
            "TotalWasteDisposed",
            "WasteIntensityPerRupeeOfTurnover",
        ],
    ),
    (
        "Consumer Responsibility",
        [
            "ConsumerComplaintsReceivedDuringTheYear",
            "ConsumerComplaintsPendingResolutionAtEndOfYear",
            "NumberOfInstancesOfDataBreaches",
            "DoesTheEntityHaveAFrameworkOrPolicyOnCyberSecurity",
        ],
    ),
    (
        "Governance & Financial",
        [
            "Turnover",
            "RevenueFromOperations",
            "TotalRevenueOfTheCompany",
            "NumberOfPenaltiesOrFinesOrPunishments",
            "NumberOfPenaltiesImposed",
        ],
    ),
]


def _matches_group(element: str, patterns: list[str]) -> bool:
    return any(pat in element for pat in patterns)


def _format_row(row: dict) -> str:
    """Format a single KPI row as 'Metric [Context]: Value (unit)'."""
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
    return f"  {label}: {value_str}"


def chunk_file(fp: Path, df) -> list[dict]:
    scalar_df, _ = filter_df(df)  # summary uses scalar facts only

    if scalar_df.empty:
        return []

    first = df[df["symbol"] != ""].iloc[0].to_dict()
    symbol = first["symbol"]
    company_name = first["companyName"]
    fy_from = first["fyFrom"]
    fy_to = first["fyTo"]

    header = f"Company: {company_name} ({symbol}) | FY: {fy_from}-{fy_to} | ESG Summary"

    sections: list[str] = []
    total_rows_used = 0

    for section_label, patterns in KPI_GROUPS:
        # Find all rows matching this section's KPI patterns
        matching = [
            row
            for row in scalar_df.to_dict("records")
            if _matches_group(row["element"], patterns)
        ]
        if not matching:
            continue

        section_lines = [f"\n=== {section_label} ==="]
        for row in matching:
            section_lines.append(_format_row(row))
        sections.append("\n".join(section_lines))
        total_rows_used += len(matching)

    if not sections:
        return []

    text = header + "\n" + "\n".join(sections)

    return [
        {
            "chunk_id": f"s5_{symbol}_{fy_from}_{fy_to}_summary",
            "text": text,
            "metadata": {
                "strategy": STRATEGY,
                "symbol": symbol,
                "companyName": company_name,
                "fyFrom": fy_from,
                "fyTo": fy_to,
                "kpi_row_count": total_rows_used,
                "source_file": fp.name,
            },
        }
    ]


def run(limit: int | None = None) -> None:
    all_chunks: list[dict] = []
    files = list(iter_clean_files())
    if limit:
        files = files[:limit]

    for fp, df in tqdm(files, desc="Strategy 5 — Company Summary"):
        all_chunks.extend(chunk_file(fp, df))

    out_path = write_jsonl(all_chunks, OUT_DIR)
    print(f"Written {len(all_chunks):,} chunks → {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Strategy 5: company-level ESG summary"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Process only first N files"
    )
    args = parser.parse_args()
    run(limit=args.limit)
