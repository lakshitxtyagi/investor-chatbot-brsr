"""
compare.py — Side-by-side ESG company comparison from BRSR CSVs
===============================================================
Reads cleaned BRSR CSV files directly (no Weaviate) and extracts
standardised metrics grouped into sections:

  1. Company Overview
  2. Financial
  3. Workforce
  4. Health & Safety
  5. GHG Emissions
  6. Energy
  7. Water
  8. Waste
  9. Governance & Compliance
  10. CSR

Each section returns a list of {label, value, unit} rows for each company.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_CLEAN_DIR = Path(__file__).parent.parent / "brsr-data" / "clean"

# ---------------------------------------------------------------------------
# Company index (built lazily, maps UPPER-CASE symbol → Path)
# ---------------------------------------------------------------------------
_INDEX: dict[str, Path] | None = None


def _build_index() -> dict[str, Path]:
    idx: dict[str, Path] = {}
    for p in _CLEAN_DIR.glob("*_clean.csv"):
        symbol = p.name.split("_")[0].upper()
        idx[symbol] = p
    return idx


def _get_index() -> dict[str, Path]:
    global _INDEX
    if _INDEX is None:
        _INDEX = _build_index()
    return _INDEX


# ---------------------------------------------------------------------------
# Public: list available symbols
# ---------------------------------------------------------------------------

def list_symbols() -> list[str]:
    return sorted(_get_index().keys())


# ---------------------------------------------------------------------------
# Company file resolver
# ---------------------------------------------------------------------------

def _resolve_symbol(query: str) -> str:
    """Return a canonical UPPER-CASE symbol matching query (symbol or partial company name)."""
    idx = _get_index()
    upper = query.strip().upper()
    if upper in idx:
        return upper

    # Try prefix match on symbol
    matches = [s for s in idx if s.startswith(upper)]
    if len(matches) == 1:
        return matches[0]

    # Try searching company name inside each CSV's first row
    for symbol, path in idx.items():
        try:
            row = pd.read_csv(path, nrows=5)
            names = row["companyName"].dropna().tolist()
            for name in names:
                if upper in str(name).upper():
                    return symbol
        except Exception:
            continue

    raise ValueError(f"Company '{query}' not found. Available symbols: {', '.join(sorted(idx)[:20])} ...")


# ---------------------------------------------------------------------------
# Data loading & cleaning
# ---------------------------------------------------------------------------

def _load_df(symbol: str) -> pd.DataFrame:
    path = _get_index()[symbol]
    df = pd.read_csv(path, dtype=str)
    # Drop taxonomy placeholder rows
    mask_domain = df["element"].str.lower().str.endswith(("domain", "member"), na=False)
    df = df[~mask_domain].copy()
    df["value_num"] = pd.to_numeric(df["value"], errors="coerce")
    df["dim"] = df["dimensions"].fillna("").str.lower()
    return df


# ---------------------------------------------------------------------------
# Dimension helpers
# ---------------------------------------------------------------------------

def _pick(df: pd.DataFrame, element_pat: str, dim_kws: list[str] | None = None,
          exclude_dim_kws: list[str] | None = None,
          period: str = "current") -> float | None:
    """
    Find the first numeric value in df matching element_pat and dim_kws.

    period: "current" takes the first row (latest FY), "prior" takes the second.
    """
    rows = df[df["element"].str.contains(element_pat, case=False, na=False, regex=True)]
    if dim_kws:
        for kw in dim_kws:
            rows = rows[rows["dim"].str.contains(kw, case=False, na=False)]
    if exclude_dim_kws:
        for kw in exclude_dim_kws:
            rows = rows[~rows["dim"].str.contains(kw, case=False, na=False)]
    rows = rows.dropna(subset=["value_num"])
    if rows.empty:
        return None
    idx = 0 if period == "current" else (1 if len(rows) > 1 else 0)
    return float(rows.iloc[idx]["value_num"])


def _pick_text(df: pd.DataFrame, element_pat: str) -> str | None:
    rows = df[df["element"].str.contains(element_pat, case=False, na=False, regex=True)]
    rows = rows[rows["value"].notna() & (rows["value"].str.strip() != "")]
    if rows.empty:
        return None
    return str(rows.iloc[0]["value"]).strip()


def _unit(df: pd.DataFrame, element_pat: str) -> str:
    rows = df[df["element"].str.contains(element_pat, case=False, na=False, regex=True)]
    rows = rows[rows["unit"].notna()]
    if rows.empty:
        return ""
    return str(rows.iloc[0]["unit"])


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _fmt(v: float | None, unit: str = "", decimals: int = 2) -> str:
    if v is None:
        return "—"
    if unit == "INR":
        if v >= 1e9:
            return f"₹{v/1e7:,.1f} Cr"
        if v >= 1e5:
            return f"₹{v/1e5:,.1f} L"
        return f"₹{v:,.0f}"
    if unit in ("pure", "%", "") and abs(v) <= 10:
        return f"{v:.{decimals}f}"
    if unit == "pure" and v > 10:
        return f"{v:,.0f}"
    return f"{v:,.{decimals}f} {unit}".strip()


def _metric(label: str, v: float | None, unit: str = "", decimals: int = 2,
            lower_is_better: bool = False) -> dict[str, Any]:
    return {
        "label": label,
        "raw": v,
        "display": _fmt(v, unit, decimals),
        "unit": unit,
        "lower_is_better": lower_is_better,
    }


# ---------------------------------------------------------------------------
# Section extractors
# ---------------------------------------------------------------------------

def _section_overview(df: pd.DataFrame, symbol: str) -> list[dict]:
    company_name = _pick_text(df, r"NameOfTheCompany") or _pick_text(df, r"companyName") or symbol
    fy_rows = df[df["fyTo"].notna()]
    fy = str(fy_rows.iloc[0]["fyTo"])[:4] if not fy_rows.empty else "—"
    cin = _pick_text(df, r"CorporateIdentityNumber")
    sector = _pick_text(df, r"SectorOfTheCompany|NatureOfBusiness")
    paid_up = _pick(df, r"ValueOfSharesPaidUp")
    net_worth = _pick(df, r"NetWorth")
    return [
        {"label": "Company Name", "raw": None, "display": company_name, "unit": "", "lower_is_better": False},
        {"label": "FY", "raw": None, "display": fy, "unit": "", "lower_is_better": False},
        {"label": "CIN", "raw": None, "display": cin or "—", "unit": "", "lower_is_better": False},
        {"label": "Sector / Nature", "raw": None, "display": sector or "—", "unit": "", "lower_is_better": False},
        _metric("Paid-up Capital", paid_up, "INR"),
        _metric("Net Worth", net_worth, "INR"),
    ]


def _section_financial(df: pd.DataFrame) -> list[dict]:
    revenue = _pick(df, r"TotalRevenueOfTheCompany|RevenueFromOperations")
    export_pct = _pick(df, r"PercentageOfContributionOfExports")
    business_pct = _pick(df, r"PercentageOfTotalTurnoverForBusinessActivities")
    wellbeing_pct = _pick(df, r"PercentageOfCostIncurredOnWellBeing.*TotalRevenue")
    return [
        _metric("Total Revenue", revenue, "INR"),
        _metric("Export % of Turnover", export_pct, "%", decimals=1),
        _metric("Business Activity % of Turnover", business_pct, "%", decimals=1),
        _metric("Well-being Cost % of Revenue", wellbeing_pct, "%", decimals=2),
    ]


def _section_workforce(df: pd.DataFrame) -> list[dict]:
    emp = "NumberOfEmployeesOrWorkersIncludingDifferentlyAbled"
    total_perm = _pick(df, emp, ["gendermember", "permanentemployees"])
    male_perm = _pick(df, emp, ["malemember", "permanentemployees"])
    female_perm = _pick(df, emp, ["femalemember", "permanentemployees"])
    total_contract = _pick(df, emp, ["gendermember", "otherthanpermanent"])
    attrition_total = _pick(df, r"TurnoverRate", ["gendermember", "permanentemployees"])
    attrition_m = _pick(df, r"TurnoverRate", ["malemember"])
    attrition_f = _pick(df, r"TurnoverRate", ["femalemember"])
    differently_abled = _pick(df, r"NumberOfDifferentlyAbledEmployeesOrWorkers")
    return [
        _metric("Permanent Employees (Total)", total_perm, ""),
        _metric("  — Male", male_perm, ""),
        _metric("  — Female", female_perm, ""),
        _metric("Contractual / Other Employees", total_contract, ""),
        _metric("Attrition Rate (Overall)", attrition_total, "%", decimals=2),
        _metric("  — Male", attrition_m, "%", decimals=2, lower_is_better=True),
        _metric("  — Female", attrition_f, "%", decimals=2, lower_is_better=True),
        _metric("Differently Abled Employees", differently_abled, ""),
    ]


def _section_health_safety(df: pd.DataFrame) -> list[dict]:
    fat_emp = _pick(df, r"NumberOfFatalities", ["employeesmember"])
    fat_wrk = _pick(df, r"NumberOfFatalities", ["workersmember"])
    ltifr_emp = _pick(df, r"LostTimeInjuryFrequencyRate", ["employeesmember"])
    ltifr_wrk = _pick(df, r"LostTimeInjuryFrequencyRate", ["workersmember"])
    trained_total = _pick(df, r"NumberOfTrainedEmployeesOrWorkers", ["gendermember"])
    total_perm = _pick(df, r"NumberOfEmployeesOrWorkersIncludingDifferentlyAbled", ["gendermember", "permanentemployees"])
    trained_pct = round(trained_total / total_perm * 100, 1) if trained_total and total_perm and total_perm > 0 else None
    return [
        _metric("Fatalities — Employees", fat_emp, "", decimals=0, lower_is_better=True),
        _metric("Fatalities — Workers", fat_wrk, "", decimals=0, lower_is_better=True),
        _metric("LTIFR — Employees", ltifr_emp, "per M hrs", decimals=3, lower_is_better=True),
        _metric("LTIFR — Workers", ltifr_wrk, "per M hrs", decimals=3, lower_is_better=True),
        _metric("Trained Employees (Total)", trained_total, ""),
        _metric("Training Coverage %", trained_pct, "%", decimals=1),
    ]


def _section_ghg(df: pd.DataFrame) -> list[dict]:
    s1 = _pick(df, r"TotalScope1Emissions$")
    s2 = _pick(df, r"TotalScope2Emissions$")
    total = (s1 or 0) + (s2 or 0) if s1 is not None or s2 is not None else None
    intensity = _pick(df, r"TotalScope1AndScope2EmissionsIntensity.*Turnover$")
    return [
        _metric("Scope 1 Emissions", s1, "MtCO2e", decimals=0, lower_is_better=True),
        _metric("Scope 2 Emissions", s2, "MtCO2e", decimals=0, lower_is_better=True),
        _metric("Total (S1+S2)", total, "MtCO2e", decimals=0, lower_is_better=True),
        _metric("GHG Intensity (per ₹ Turnover)", intensity, "MtCO2e", decimals=12, lower_is_better=True),
    ]


def _section_energy(df: pd.DataFrame) -> list[dict]:
    renew = _pick(df, r"TotalEnergyConsumedFromRenewableSources$")
    non_renew = _pick(df, r"TotalEnergyConsumedFromNonRenewableSources$")
    total = (renew or 0) + (non_renew or 0) if renew is not None or non_renew is not None else None
    pct_renew = round(renew / total * 100, 1) if renew and total and total > 0 else None
    intensity = _pick(df, r"EnergyIntensityPerRupee|EnergyIntensity.*Turnover")
    return [
        _metric("Renewable Energy", renew, "GJ", decimals=0),
        _metric("Non-Renewable Energy", non_renew, "GJ", decimals=0, lower_is_better=True),
        _metric("Total Energy Consumed", total, "GJ", decimals=0),
        _metric("% Renewable", pct_renew, "%", decimals=1),
        _metric("Energy Intensity (per ₹ Turnover)", intensity, "GJ", decimals=12, lower_is_better=True),
    ]


def _section_water(df: pd.DataFrame) -> list[dict]:
    surface = _pick(df, r"WaterWithdrawalBySurfaceWater$")
    ground = _pick(df, r"WaterWithdrawalByGroundwater$")
    third = _pick(df, r"WaterWithdrawalByThirdPartyWater$")
    total_w = (surface or 0) + (ground or 0) + (third or 0)
    total_w = total_w if total_w > 0 else None
    discharge = _pick(df, r"TotalWaterDischarge$|TotalWaterDischargedToDestination")
    consumption = _pick(df, r"TotalWaterConsumption$")
    intensity = _pick(df, r"WaterIntensity.*Turnover|WaterConsumptionIntensity")
    return [
        _metric("Water Withdrawal (Total)", total_w, "kl", decimals=0, lower_is_better=True),
        _metric("  — Surface", surface, "kl", decimals=0),
        _metric("  — Groundwater", ground, "kl", decimals=0),
        _metric("  — Third-Party", third, "kl", decimals=0),
        _metric("Water Discharge", discharge, "kl", decimals=0),
        _metric("Water Consumption", consumption, "kl", decimals=0, lower_is_better=True),
        _metric("Water Intensity (per ₹ Turnover)", intensity, "kl", decimals=12, lower_is_better=True),
    ]


def _section_waste(df: pd.DataFrame) -> list[dict]:
    generated = _pick(df, r"TotalWasteGenerated$")
    recovered = _pick(df, r"TotalWasteRecovered$")
    hazardous = _pick(df, r"TotalHazardousWasteGenerated$")
    non_haz = _pick(df, r"OtherNonHazardousWasteGenerated$|TotalNonHazardousWasteGenerated")
    recovery_pct = round(recovered / generated * 100, 1) if recovered and generated and generated > 0 else None
    return [
        _metric("Total Waste Generated", generated, "t", decimals=2, lower_is_better=True),
        _metric("  — Hazardous", hazardous, "t", decimals=2, lower_is_better=True),
        _metric("  — Non-Hazardous", non_haz, "t", decimals=2, lower_is_better=True),
        _metric("Total Waste Recovered", recovered, "t", decimals=2),
        _metric("Recovery Rate %", recovery_pct, "%", decimals=1),
    ]


def _section_governance(df: pd.DataFrame) -> list[dict]:
    filed = _pick(df, r"NumberOfComplaintsFiledFromStakeHolderGroup.*DuringTheYear")
    pending = _pick(df, r"NumberOfComplaintsPending.*AtTheEndOfYear")
    grievances = _pick(df, r"NumberOfGrievancesFiledOrReceived")
    penalties = _pick(df, r"NumberOfFinesOrPenaltiesImposed|NumberOfPenalties")
    return [
        _metric("Total Complaints Filed", filed, "", decimals=0, lower_is_better=True),
        _metric("Complaints Pending (EOY)", pending, "", decimals=0, lower_is_better=True),
        _metric("Grievances Filed", grievances, "", decimals=0, lower_is_better=True),
        _metric("Fines / Penalties", penalties, "", decimals=0, lower_is_better=True),
    ]


def _section_csr(df: pd.DataFrame) -> list[dict]:
    beneficiaries = _pick(df, r"NumberOfPersonsBenefittedFromCSRProjects")
    csr_spend = _pick(df, r"AmountSpentOnCsrActivities|TotalAmountSpentOnCsr|TotalCsrExpenditure")
    obligation = _pick(df, r"CsrObligationForTheYear|PrescribedCsrExpenditure")
    return [
        _metric("CSR Spend", csr_spend, "INR"),
        _metric("CSR Obligation", obligation, "INR"),
        _metric("Beneficiaries", beneficiaries, "", decimals=0),
    ]


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------

_SECTIONS = [
    ("Company Overview", _section_overview),
    ("Financial Performance", _section_financial),
    ("Workforce", _section_workforce),
    ("Health & Safety", _section_health_safety),
    ("GHG Emissions", _section_ghg),
    ("Energy Consumption", _section_energy),
    ("Water Management", _section_water),
    ("Waste Management", _section_waste),
    ("Governance & Compliance", _section_governance),
    ("CSR", _section_csr),
]


def compare_companies(company1: str, company2: str) -> dict[str, Any]:
    """
    Return a comparison dict:
    {
      "company1": {"symbol": ..., "name": ...},
      "company2": {"symbol": ..., "name": ...},
      "sections": [
        {"title": "...", "metrics": [
          {"label": "...", "c1": {"display": "...", "raw": float|None, ...},
                           "c2": {"display": "...", "raw": float|None, ...},
                           "winner": "c1"|"c2"|None, "lower_is_better": bool}
        ]}
      ]
    }
    """
    sym1 = _resolve_symbol(company1)
    sym2 = _resolve_symbol(company2)

    df1 = _load_df(sym1)
    df2 = _load_df(sym2)

    name1 = _pick_text(df1, r"NameOfTheCompany") or sym1
    name2 = _pick_text(df2, r"NameOfTheCompany") or sym2

    sections_out = []
    for title, extractor in _SECTIONS:
        if extractor == _section_overview:
            m1 = extractor(df1, sym1)
            m2 = extractor(df2, sym2)
        else:
            m1 = extractor(df1)
            m2 = extractor(df2)

        metrics_out = []
        for r1, r2 in zip(m1, m2):
            winner = None
            lib = r1.get("lower_is_better", False)
            raw1, raw2 = r1["raw"], r2["raw"]
            if raw1 is not None and raw2 is not None and raw1 != raw2:
                if lib:
                    winner = "c1" if raw1 < raw2 else "c2"
                else:
                    winner = "c1" if raw1 > raw2 else "c2"
            metrics_out.append({
                "label": r1["label"],
                "c1": {"display": r1["display"], "raw": raw1},
                "c2": {"display": r2["display"], "raw": raw2},
                "winner": winner,
                "lower_is_better": lib,
            })
        sections_out.append({"title": title, "metrics": metrics_out})

    return {
        "company1": {"symbol": sym1, "name": name1},
        "company2": {"symbol": sym2, "name": name2},
        "sections": sections_out,
    }
