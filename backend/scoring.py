"""
scoring.py — ESG Company Scoring from BRSR CSV Data
=====================================================
Ports the SRS.ipynb social scoring logic (TOS/SRS) and combines it with
environmental and governance metrics extracted from the cleaned BRSR CSVs.

Composite Score (0-100):
    ESG = 0.50 × EnvScore + 0.35 × SocialScore + 0.15 × GovScore

Social Score (SRS port):
    Per principle TOS = 0.25×SS + 0.15×AS + 0.25×CCS + 0.20×OES + 0.10×RTS + 0.05×TS
    Overall_TOS = 0.45×P3 + 0.25×P5 + 0.15×P8 + 0.15×P9
    SRS (sector-relative) = (1 - (TOS - min) / (max - min)) × 100
    SocialScore = 100 - SRS

Environmental Score: sector-normalized GHG intensity + renewable % + water intensity + waste recovery
Governance Score: complaints resolution rate + penalty absence
"""

from __future__ import annotations

import json
import math
import re
import statistics
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_BACKEND_DIR = Path(__file__).parent
_CLEAN_DIR   = _BACKEND_DIR.parent / "brsr-data" / "clean"
_CACHE_FILE  = _BACKEND_DIR / "companies_cache.json"

# ---------------------------------------------------------------------------
# SRS notebook constants (ported exactly from SRS.ipynb)
# ---------------------------------------------------------------------------
_RE_NUMBER  = re.compile(r"(?:(?:\d{1,3}(?:,\d{3})+)|\d+)(?:\.\d+)?%?")
_RE_YEAR    = re.compile(r"\b(19|20)\d{2}\b")
_RE_VERB    = re.compile(
    r"\b(implemented|implement|trained|train|deployed|deploy|audited|audit|"
    r"conducted|conduct|reduced|increase|increased|launched|established|"
    r"resolve|resolved|remediated|nominate|nominated|deployment|nomination|"
    r"conducting|periodic|regular|advisory|advisories|drill|drills)\b", re.I)
_POSITIVE   = re.compile(
    r"\b(reduced|improved|resolved|achieved|completed|compliant|mitigated|"
    r"certified|implemented|regular|periodic|trained|established|launched)\b", re.I)
_NEGATIVE   = re.compile(
    r"\b(incident|complaint|non-compliance|violation|increased risk|"
    r"accident|claim|fatality|injury)\b", re.I)

_TOS_WEIGHTS = {"SS": 0.25, "AS": 0.15, "CCS": 0.25, "OES": 0.20, "RTS": 0.10, "TS": 0.05}
_PRINCIPLE_WEIGHTS = {"P3": 0.45, "P5": 0.25, "P8": 0.15, "P9": 0.15}

_PRINCIPLE_ELEMENTS: dict[str, list[str]] = {
    "P3": [
        "DetailsOfMechanismAvailableToReceiveAndRedressGrievancesForPermanentWorkersExplanatoryTextBlock",
        "DetailsOfMechanismAvailableToReceiveAndRedressGrievancesForOtherThanPermanentWorkersExplanatoryTextBlock",
        "DetailsOfMechanismAvailableToReceiveAndRedressGrievancesForPermanentEmployeesExplanatoryTextBlock",
        "DetailsOfMechanismAvailableToReceiveAndRedressGrievancesForOtherThanPermanentEmployeesExplanatoryTextBlock",
        "DetailsOfOccupationalHealthAndSafetyManagementSystemExplanatoryTextBlock",
        "DesclosureOfTheProcessesUsedToIdentifyWorkRelatedHazardsAndAssessRisksOnARoutineAndNonRoutineBasisByTheEntityExplanatoryTextBlock",
        "DescribeTheMeasuresTakenByTheEntityToEnsureASafeAndHealthyWorkPlaceExplanatoryTextBlock",
        "DetailsOfAnyCorrectiveActionTakenOrUnderwayToAddressSafetyRelatedIncidentsOfYourPlantsAndOfficesThatWereAssessedExplanatoryTextBlock",
    ],
    "P5": [
        "DescribeTheInternalMechanismsInPlaceToRedressGrievancesRelatedToHumanRightsIssuesExplanatoryTextBlock",
        "MechanismsToPreventAdverseConsequencesToTheComplainantInDiscriminationAndHarassmentCasesExplanatoryTextBlock",
        "DetailsOfAnyCorrectiveActionsTakenOrUnderwayToAddressSignificantRisksOrConcernsArisingFromTheAssessmentsOfPlantAndOfficeExplanatoryTextBlock",
        "DetailsOfABusinessProcessBeingModifiedOrIntroducedAsAResultOfAddressingHumanRightsGrievancesOrComplaintsExplanatoryTextBlock",
    ],
    "P8": [
        "DescribeTheMechanismsToReceiveAndRedressGrievancesOfTheCommunityExplanatoryTextBlock",
        "DetailsOfMeasuresUndertakenByTheEntityToEnsureThatStatutoryDuesHaveBeenDeductedAndDepositedByTheValueChainPartnersExplanatoryTextBlock",
        "DetailsOfAnyCorrectiveActionTakenOrUnderwayToAddressSafetyRelatedIncidentsOnAssessmentOfValueChainPartnersExplanatoryTextBlock",
    ],
    "P9": [
        "DescribeTheMechanismsInPlaceToReceiveAndRespondToConsumerComplaintsAndFeedbackExplanatoryTextBlock",
        "DetailsOfImpactOfDataBreachesExplanatoryTextBlock",
        "DetailsOfAnyCorrectiveActionsTakenOrUnderwayOnIssuesRelatingToAdvertisingAndDeliveryOfEssentialServicesOrCyberSecurityAndDataPrivacyOrRecallsOrPenaltyOrActionTakenByRegulatoryAuthoritiesOnSafetyOfProductsOrServicesExplanatoryTextBlock",
    ],
}

_EXPECTED_THEMES: dict[str, list[str]] = {
    "P3": ["grievance", "occupational health", "safety", "training", "incident",
           "health", "workers", "employees", "hazard", "risk assessment", "osh"],
    "P5": ["human rights", "discrimination", "harassment", "posh", "grievance",
           "child labour", "forced labour", "diversity", "supplier due diligence"],
    "P8": ["community", "csr", "value chain", "supplier", "contractor",
           "statutory", "compliance", "grievance", "inclusive"],
    "P9": ["consumer", "complaint", "feedback", "data breach", "cyber security",
           "privacy", "product safety", "advertising", "recall"],
}

# ---------------------------------------------------------------------------
# Grade and sector color mapping
# ---------------------------------------------------------------------------
_GRADE_THRESHOLDS = [
    (85, "A+"), (75, "A"), (65, "A-"), (55, "B+"), (45, "B"), (35, "B-"),
]
_SECTOR_COLORS: dict[str, str] = {
    "Information, Communication & Technology": "#6366f1",
    "IT & Software": "#6366f1",
    "Financial Services": "#22d3ee",
    "Manufacturing & Engineering": "#f59e0b",
    "Mining and Metals": "#f59e0b",
    "Oil, Gas & Consumable Fuels": "#ef4444",
    "Power Generation and Transmission": "#ef4444",
    "FMCG": "#22c55e",
    "Healthcare": "#a78bfa",
    "Chemicals": "#fb923c",
    "Transportation and Automotive": "#38bdf8",
    "Infrastructure and Construction": "#fbbf24",
    "Real Estate & Construction": "#e879f9",
    "Financial": "#22d3ee",
    "Energy": "#ef4444",
    "Manufacturing": "#f59e0b",
}


def _grade(score: float) -> str:
    for threshold, g in _GRADE_THRESHOLDS:
        if score >= threshold:
            return g
    return "C"


def _sector_color(sector: str) -> str:
    return _SECTOR_COLORS.get(sector, "#64748b")


# ---------------------------------------------------------------------------
# SRS NLP — fallback extractor (ported from notebook Cell 2)
# ---------------------------------------------------------------------------

def _fallback_extract(text: str) -> dict[str, Any]:
    if not text or not text.strip():
        return {"actions": [], "numbers": [], "timeframes": [],
                "themes": [], "evidence": [], "tone": "neutral"}
    lines = [line.strip() for line in re.split(r"[\n\r]+", text) if line.strip()]
    sents = [s.strip() for s in re.split(r"(?<=[.?!])\s+", text) if s.strip()]

    action_candidates: list[str] = []
    for line in lines:
        if re.match(r"^[-*\da)\.]+\s+", line) or _RE_VERB.search(line):
            action_candidates.append(re.sub(r"^[-*\d\.\)\s]+", "", line))
    for sent in sents:
        if _RE_VERB.search(sent) and sent not in action_candidates:
            action_candidates.append(sent)

    numbers    = _RE_NUMBER.findall(text)
    timeframes = [m.group(0) for m in _RE_YEAR.finditer(text)]
    flat_themes = {t.lower() for lst in _EXPECTED_THEMES.values() for t in lst}
    themes_found = [t for t in flat_themes
                    if re.search(r"\b" + re.escape(t) + r"\b", text, re.I)]
    evidence_sents = [s for s in sents
                      if _RE_NUMBER.search(s) or re.search(
                          r"\b(reduced|decreased|increased|achieved|improved|resulted|"
                          r"fatality|lost time|ltifr|trir|led to|periodic|regular|drill|training)\b",
                          s, re.I)]
    pos  = len(_POSITIVE.findall(text))
    neg  = len(_NEGATIVE.findall(text))
    tone = "positive" if pos > neg else ("negative" if neg > pos else "neutral")

    return {"actions": action_candidates, "numbers": numbers, "timeframes": timeframes,
            "themes": themes_found, "evidence": evidence_sents, "tone": tone}


def _is_substantive(text: str) -> bool:
    if not text or str(text).strip().lower() in ("", "nan", "true", "false"):
        return False
    try:
        float(str(text).replace(",", ""))
        return False
    except ValueError:
        pass
    if re.match(r"\d{4}-\d{2}-\d{2}", str(text).strip()):
        return False
    return len(str(text).strip()) >= 10


# ---------------------------------------------------------------------------
# SRS TOS computation (ported from notebook Cell 3)
# ---------------------------------------------------------------------------

def _compute_tos(text: str, principle: str) -> float:
    """Compute TOS for a single text block and principle."""
    if not text.strip():
        return 0.0

    ext = _fallback_extract(text)
    expected_themes = [t.lower() for t in _EXPECTED_THEMES.get(principle, [])]

    N_numbers  = len(ext["numbers"])
    N_actions  = len(ext["actions"])
    N_evidence = len(ext["evidence"])
    N_sents    = max(1, len(re.split(r"(?<=[.\n])\s+", text)))

    # SS — Specificity Score
    alpha, beta, gamma = 0.4, 0.5, 0.1
    raw_ss  = alpha * min(N_numbers, 2) + beta * min(N_actions, 6) + gamma * N_evidence
    max_raw = alpha * 2 + beta * 6 + gamma * 2
    SS = max(0.0, min(1.0,
             (raw_ss / max_raw) / (1 if N_sents <= 3 else math.log(1 + N_sents))))

    # AS — Actionability Score
    strong_v = len(_RE_VERB.findall(text))
    AS = min(1.0, len(ext["actions"]) / 3.0)
    if strong_v >= 2:
        AS = min(1.0, AS + 0.1)

    # CCS — Content Coverage Score
    found   = {t.lower() for t in ext["themes"]}
    exp_set = set(expected_themes)
    CCS     = (len(found & exp_set) / len(exp_set)) if exp_set else 0.0

    # OES — Outcome Evidence Score
    N_num  = len(ext["numbers"])
    N_time = len(ext["timeframes"])
    N_evid = len(ext["evidence"])
    OES    = min(1.0,
                 0.4 * min(1.0, N_num  / 2.0) +
                 0.3 * min(1.0, N_time / 1.0) +
                 0.3 * min(1.0, N_evid / 1.0))

    # RTS — Reporting Tone Score
    RTS = {"positive": 1.0, "neutral": 0.5, "negative": 0.0}.get(ext["tone"], 0.5)

    # TS — Text Score (log-length × SS)
    L     = len(text.split())
    log_L = math.log(1 + L)
    TS    = max(0.0, min(1.0, (log_L * SS) / (1 + log_L)))

    TOS = (
        _TOS_WEIGHTS["SS"]  * SS  +
        _TOS_WEIGHTS["AS"]  * AS  +
        _TOS_WEIGHTS["CCS"] * CCS +
        _TOS_WEIGHTS["OES"] * OES +
        _TOS_WEIGHTS["RTS"] * RTS +
        _TOS_WEIGHTS["TS"]  * TS
    )
    return round(TOS, 6)


# ---------------------------------------------------------------------------
# Sector classifier — NIC code + keyword matching on DescriptionOfMainActivity
# ---------------------------------------------------------------------------

_NIC_SECTOR: list[tuple[str, str]] = [
    ("620", "Information, Communication & Technology"),
    ("63",  "Information, Communication & Technology"),
    ("61",  "Telecom"),
    ("62",  "Information, Communication & Technology"),
    ("641", "Financial Services"), ("642", "Financial Services"),
    ("643", "Financial Services"), ("649", "Financial Services"),
    ("651", "Financial Services"), ("652", "Financial Services"),
    ("661", "Financial Services"), ("662", "Financial Services"),
    ("663", "Financial Services"), ("664", "Financial Services"),
    ("241", "Mining and Metals"),  ("242", "Mining and Metals"),
    ("243", "Mining and Metals"),  ("244", "Mining and Metals"),
    ("72",  "Mining and Metals"),
    ("191", "Oil, Gas & Consumable Fuels"), ("192", "Oil, Gas & Consumable Fuels"),
    ("193", "Oil, Gas & Consumable Fuels"), ("060", "Oil, Gas & Consumable Fuels"),
    ("061", "Oil, Gas & Consumable Fuels"), ("062", "Oil, Gas & Consumable Fuels"),
    ("201", "Chemicals"), ("202", "Chemicals"), ("203", "Chemicals"),
    ("204", "Chemicals"), ("205", "Chemicals"), ("206", "Chemicals"),
    ("207", "Chemicals"),
    ("210", "Healthcare"),
    ("271", "Consumer Durables"), ("272", "Consumer Durables"),
    ("273", "Consumer Durables"),
    ("261", "Consumer Durables"), ("262", "Consumer Durables"),
    ("263", "Consumer Durables"),
    ("281", "Industrial Products and Equipment"),
    ("282", "Industrial Products and Equipment"),
    ("289", "Industrial Products and Equipment"),
    ("291", "Transportation and Automotive"),
    ("292", "Transportation and Automotive"),
    ("293", "Transportation and Automotive"),
    ("301", "Apparel, Garments and Textiles"),
    ("302", "Apparel, Garments and Textiles"),
    ("131", "Apparel, Garments and Textiles"),
    ("139", "Apparel, Garments and Textiles"),
    ("141", "Apparel, Garments and Textiles"),
    ("351", "Power Generation and Transmission"),
    ("352", "Power Generation and Transmission"),
    ("353", "Power Generation and Transmission"),
    ("471", "Retail"), ("472", "Retail"), ("473", "Retail"),
    ("461", "Retail"), ("462", "Retail"),
    ("551", "Services"), ("552", "Services"), ("559", "Services"),
    ("561", "Services"), ("562", "Services"),
    ("860", "Healthcare"), ("861", "Healthcare"), ("862", "Healthcare"),
    ("411", "Infrastructure and Construction"),
    ("412", "Infrastructure and Construction"),
    ("421", "Infrastructure and Construction"),
    ("681", "Real Estate & Construction"),
    ("682", "Real Estate & Construction"),
    ("685", "Real Estate & Construction"),
    ("011", "Forestry and Forest Products"),
    ("012", "Forestry and Forest Products"),
    ("020", "Forestry and Forest Products"),
    ("110", "Breweries, Distilleries and Beverages"),
    ("107", "FMCG"),
    ("108", "FMCG"), ("109", "FMCG"),
    ("581", "Media and Entertainment"),
    ("591", "Media and Entertainment"),
    ("601", "Media and Entertainment"),
    ("602", "Media and Entertainment"),
    ("711", "Industrial Products and Equipment"),
    ("712", "Industrial Products and Equipment"),
    ("900", "Leisure and Recreation Services"),
]

_KW_SECTOR: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(software|IT|information technology|consulting|digital|cloud|technical services|professional.*technical)\b", re.I),
     "Information, Communication & Technology"),
    (re.compile(r"\b(bank|banking|nbfc|financial|insurance|asset management|wealth|brokerage|fintech)\b", re.I),
     "Financial Services"),
    (re.compile(r"\b(steel|iron|metal|aluminium|copper|zinc|lead)\b", re.I),
     "Mining and Metals"),
    (re.compile(r"\b(oil|petroleum|refinery|gas|lng|hydrocarbon|fuel)\b", re.I),
     "Oil, Gas & Consumable Fuels"),
    (re.compile(r"\b(power|electricity|generation|transmission|solar|wind|renewable energy)\b", re.I),
     "Power Generation and Transmission"),
    (re.compile(r"\b(pharma|pharmaceutical|drug|medicine|hospital|healthcare|biotech|diagnostics)\b", re.I),
     "Healthcare"),
    (re.compile(r"\b(chemical|specialty chemical|agrochemical|fertilizer|polymer)\b", re.I),
     "Chemicals"),
    (re.compile(r"\b(FMCG|consumer goods|food|beverages|personal care|household)\b", re.I),
     "FMCG"),
    (re.compile(r"\b(automobile|automotive|vehicle|two-?wheeler|tractor)\b", re.I),
     "Transportation and Automotive"),
    (re.compile(r"\b(textile|apparel|garment|fashion|yarn|fabric)\b", re.I),
     "Apparel, Garments and Textiles"),
    (re.compile(r"\b(real estate|housing|construction|developer|realty)\b", re.I),
     "Real Estate & Construction"),
    (re.compile(r"\b(infrastructure|roads|highways|airports|ports|engineering)\b", re.I),
     "Infrastructure and Construction"),
    (re.compile(r"\b(retail|e-commerce|supermarket|hypermarket|trading)\b", re.I),
     "Retail"),
    (re.compile(r"\b(media|entertainment|television|publishing|broadcasting|film)\b", re.I),
     "Media and Entertainment"),
    (re.compile(r"\b(hotel|hospitality|tourism|restaurant|travel)\b", re.I),
     "Services"),
    (re.compile(r"\b(mining|coal|bauxite|iron ore|mineral)\b", re.I),
     "Mining and Metals"),
]


def _classify_sector(df: pd.DataFrame) -> str:
    # 1. Try keyword match on DescriptionOfMainActivity
    desc_rows = df[df["element"] == "DescriptionOfMainActivity"]
    for _, row in desc_rows.iterrows():
        text = str(row["value"]) if pd.notna(row["value"]) else ""
        for pat, sector in _KW_SECTOR:
            if pat.search(text):
                return sector

    # 2. Try NIC code prefix mapping
    nic_rows = df[df["element"] == "NICCodeOfProductOrServiceSoldByTheEntity"]
    for _, row in nic_rows.iterrows():
        nic = str(row["value"]).strip() if pd.notna(row["value"]) else ""
        for prefix, sector in _NIC_SECTOR:
            if nic.startswith(prefix):
                return sector

    return "Unclassified"


# ---------------------------------------------------------------------------
# Numeric helpers (shared with compare.py)
# ---------------------------------------------------------------------------

def _pick(df: pd.DataFrame, element_pat: str,
          dim_kws: list[str] | None = None,
          exclude_dim_kws: list[str] | None = None) -> float | None:
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
    return float(rows.iloc[0]["value_num"])


def _pick_text(df: pd.DataFrame, element_pat: str) -> str | None:
    rows = df[df["element"].str.contains(element_pat, case=False, na=False, regex=True)]
    rows = rows[rows["value"].notna() & (rows["value"].str.strip() != "")]
    return str(rows.iloc[0]["value"]).strip() if not rows.empty else None


# ---------------------------------------------------------------------------
# Per-company raw data extraction
# ---------------------------------------------------------------------------

@dataclass
class _RawCompany:
    symbol: str
    name: str
    sector: str
    fy: str
    # Environmental
    scope1: float | None
    scope2: float | None
    revenue: float | None
    renewable_energy: float | None
    nonrenewable_energy: float | None
    water_withdrawal: float | None
    waste_generated: float | None
    waste_recovered: float | None
    # Prior-year environmental for trend
    scope1_prior: float | None
    scope2_prior: float | None
    renewable_prior: float | None
    # Workforce
    total_employees: float | None
    # Governance
    complaints_filed: float | None
    complaints_pending: float | None
    penalties: float | None
    # Social (TOS per principle)
    tos_p3: float
    tos_p5: float
    tos_p8: float
    tos_p9: float


def _load_and_extract(path: Path) -> _RawCompany | None:
    """Load a single CSV and extract all raw metrics."""
    try:
        symbol = path.name.split("_")[0].upper()
        df = pd.read_csv(path, dtype=str)

        mask_domain = df["element"].str.lower().str.endswith(("domain", "member"), na=False)
        df = df[~mask_domain].copy()
        df["value_num"] = pd.to_numeric(df["value"], errors="coerce")
        df["dim"] = df["dimensions"].fillna("").str.lower()

        name   = _pick_text(df, r"NameOfTheCompany") or symbol
        sector = _classify_sector(df)

        fy_rows = df[df["fyTo"].notna()]
        fy = str(fy_rows.iloc[0]["fyTo"])[:4] if not fy_rows.empty else "2025"

        # Environmental — current year (first occurrence)
        scope1     = _pick(df, r"TotalScope1Emissions$")
        scope2     = _pick(df, r"TotalScope2Emissions$")
        revenue    = _pick(df, r"TotalRevenueOfTheCompany|RevenueFromOperations")
        ren_energy = _pick(df, r"TotalEnergyConsumedFromRenewableSources$")
        non_ren    = _pick(df, r"TotalEnergyConsumedFromNonRenewableSources$")
        water_w    = _sum_water(df)
        waste_gen  = _pick(df, r"TotalWasteGenerated$")
        waste_rec  = _pick(df, r"TotalWasteRecovered$")

        # Prior-year (second row) for trend
        scope1_p   = _pick_nth(df, r"TotalScope1Emissions$", 1)
        scope2_p   = _pick_nth(df, r"TotalScope2Emissions$", 1)
        ren_p      = _pick_nth(df, r"TotalEnergyConsumedFromRenewableSources$", 1)

        # Workforce
        total_emp  = _pick(df, r"NumberOfEmployeesOrWorkersIncludingDifferentlyAbled",
                           ["gendermember", "permanentemployees"])

        # Governance
        comp_filed   = _sum_complaints(df, "filed")
        comp_pending = _sum_complaints(df, "pending")
        penalties    = _pick(df, r"NumberOfFinesOrPenaltiesImposed|NumberOfPenalties")

        # Social — text from BRSR elements
        tos_p3 = _compute_principle_tos(df, "P3")
        tos_p5 = _compute_principle_tos(df, "P5")
        tos_p8 = _compute_principle_tos(df, "P8")
        tos_p9 = _compute_principle_tos(df, "P9")

        return _RawCompany(
            symbol=symbol, name=name, sector=sector, fy=fy,
            scope1=scope1, scope2=scope2, revenue=revenue,
            renewable_energy=ren_energy, nonrenewable_energy=non_ren,
            water_withdrawal=water_w, waste_generated=waste_gen, waste_recovered=waste_rec,
            scope1_prior=scope1_p, scope2_prior=scope2_p, renewable_prior=ren_p,
            total_employees=total_emp,
            complaints_filed=comp_filed, complaints_pending=comp_pending, penalties=penalties,
            tos_p3=tos_p3, tos_p5=tos_p5, tos_p8=tos_p8, tos_p9=tos_p9,
        )
    except Exception:
        return None


def _sum_water(df: pd.DataFrame) -> float | None:
    surface = _pick(df, r"WaterWithdrawalBySurfaceWater$")
    ground  = _pick(df, r"WaterWithdrawalByGroundwater$")
    third   = _pick(df, r"WaterWithdrawalByThirdPartyWater$")
    vals    = [v for v in (surface, ground, third) if v is not None]
    return sum(vals) if vals else None


def _pick_nth(df: pd.DataFrame, element_pat: str, n: int) -> float | None:
    rows = df[df["element"].str.contains(element_pat, case=False, na=False, regex=True)]
    rows = rows.dropna(subset=["value_num"])
    if len(rows) <= n:
        return None
    return float(rows.iloc[n]["value_num"])


def _sum_complaints(df: pd.DataFrame, kind: str) -> float | None:
    pat = (r"NumberOfComplaintsFiledFromStakeHolderGroup.*DuringTheYear"
           if kind == "filed"
           else r"NumberOfComplaintsPending.*AtTheEndOfYear")
    rows = df[df["element"].str.contains(pat, case=False, na=False, regex=True)]
    rows = rows.dropna(subset=["value_num"])
    if rows.empty:
        return None
    return float(rows["value_num"].sum())


def _compute_principle_tos(df: pd.DataFrame, principle: str) -> float:
    elements = _PRINCIPLE_ELEMENTS[principle]
    parts: list[str] = []
    for elem in elements:
        matches = df[df["element"] == elem]
        if matches.empty:
            # Try case-insensitive partial match
            matches = df[df["element"].str.lower() == elem.lower()]
        for _, row in matches.iterrows():
            raw = str(row["value"]) if pd.notna(row["value"]) else ""
            if _is_substantive(raw):
                parts.append(raw.strip())
    combined = "\n\n".join(parts)
    return _compute_tos(combined, principle)


# ---------------------------------------------------------------------------
# Score computation (sector-aware normalization)
# ---------------------------------------------------------------------------

def _compute_overall_tos(raw: _RawCompany) -> float:
    return (
        _PRINCIPLE_WEIGHTS["P3"] * raw.tos_p3 +
        _PRINCIPLE_WEIGHTS["P5"] * raw.tos_p5 +
        _PRINCIPLE_WEIGHTS["P8"] * raw.tos_p8 +
        _PRINCIPLE_WEIGHTS["P9"] * raw.tos_p9
    )


def _compute_gov_score(raw: _RawCompany) -> float:
    score = 100.0
    # Penalize for pending complaints
    if raw.complaints_filed is not None and raw.complaints_filed > 0:
        pending = raw.complaints_pending or 0
        pending_rate = pending / raw.complaints_filed
        score -= min(30.0, pending_rate * 30.0)
    elif raw.complaints_pending is not None and raw.complaints_pending > 0:
        score -= 20.0
    # Penalize for penalties
    if raw.penalties is not None and raw.penalties > 0:
        score -= min(20.0, raw.penalties * 5.0)
    return max(0.0, score)


def _compute_env_raw(raw: _RawCompany) -> dict[str, float | None]:
    """Compute raw environmental metrics (pre-normalization)."""
    # Derived metrics
    ghg_total = None
    if raw.scope1 is not None or raw.scope2 is not None:
        ghg_total = (raw.scope1 or 0) + (raw.scope2 or 0)
    ghg_intensity = None
    if ghg_total is not None and raw.revenue and raw.revenue > 0:
        ghg_intensity = ghg_total / raw.revenue

    total_energy = None
    if raw.renewable_energy is not None or raw.nonrenewable_energy is not None:
        total_energy = (raw.renewable_energy or 0) + (raw.nonrenewable_energy or 0)
    renewable_pct = None
    if raw.renewable_energy is not None and total_energy and total_energy > 0:
        renewable_pct = (raw.renewable_energy / total_energy) * 100

    water_intensity = None
    if raw.water_withdrawal is not None and raw.revenue and raw.revenue > 0:
        water_intensity = raw.water_withdrawal / raw.revenue

    waste_recovery_rate = None
    if raw.waste_recovered is not None and raw.waste_generated and raw.waste_generated > 0:
        waste_recovery_rate = (raw.waste_recovered / raw.waste_generated) * 100

    return {
        "ghg_intensity": ghg_intensity,
        "renewable_pct": renewable_pct,
        "water_intensity": water_intensity,
        "waste_recovery_rate": waste_recovery_rate,
        "ghg_total": ghg_total,
        "total_energy": total_energy,
    }


def _norm_lower_better(val: float | None, lo: float, hi: float) -> float:
    """Normalize a "lower is better" metric to 0–1 (higher = better)."""
    if val is None:
        return 0.5  # neutral when data missing
    if hi <= lo:
        return 0.5
    normed = (val - lo) / (hi - lo)
    return max(0.0, min(1.0, 1.0 - normed))


def _norm_higher_better(val: float | None, lo: float, hi: float) -> float:
    if val is None:
        return 0.5
    if hi <= lo:
        return 0.5
    return max(0.0, min(1.0, (val - lo) / (hi - lo)))


def _compute_trend(raw: _RawCompany) -> str:
    ghg_cur  = (raw.scope1 or 0) + (raw.scope2 or 0) if (raw.scope1 or raw.scope2) else None
    ghg_prev = (raw.scope1_prior or 0) + (raw.scope2_prior or 0) if (raw.scope1_prior or raw.scope2_prior) else None

    ghg_improved = (ghg_cur is not None and ghg_prev is not None and
                    ghg_prev > 0 and ghg_cur < ghg_prev)
    ghg_worsened = (ghg_cur is not None and ghg_prev is not None and
                    ghg_prev > 0 and ghg_cur > ghg_prev)

    ren_cur  = raw.renewable_energy
    ren_prev = raw.renewable_prior
    ren_improved = (ren_cur is not None and ren_prev is not None and ren_cur > ren_prev)
    ren_worsened  = (ren_cur is not None and ren_prev is not None and ren_cur < ren_prev)

    positive = sum([ghg_improved, ren_improved])
    negative = sum([ghg_worsened, ren_worsened])
    if positive > negative:
        return "up"
    if negative > positive:
        return "down"
    return "neutral"


def _compute_highlights(raw: _RawCompany, env: dict, score: float) -> list[str]:
    bullets: list[str] = []
    if env.get("renewable_pct") is not None:
        bullets.append(f"{env['renewable_pct']:.0f}% renewable energy")
    if env.get("ghg_total") is not None:
        gt = env["ghg_total"]
        bullets.append(f"Scope 1+2 emissions: {gt:,.0f} MtCO2e")
    if raw.total_employees:
        bullets.append(f"Workforce: {raw.total_employees:,.0f} employees")
    if raw.waste_generated and raw.waste_recovered:
        rate = raw.waste_recovered / raw.waste_generated * 100
        bullets.append(f"Waste recovery rate: {rate:.0f}%")
    if raw.tos_p3 > 0.5:
        bullets.append("Strong worker safety & grievance disclosures")
    if raw.tos_p9 > 0.5:
        bullets.append("Robust consumer protection disclosures")
    if score >= 75:
        bullets.append("ESG leader in sector")
    return bullets[:3]


def _compute_principles(raw: _RawCompany) -> dict[str, int]:
    """Map TOS scores to principle compliance counts (P3/P5/P8/P9 + inferred for others)."""
    tos_vals = [raw.tos_p3, raw.tos_p5, raw.tos_p8, raw.tos_p9]
    compliant = sum(1 for t in tos_vals if t >= 0.5)
    partial   = sum(1 for t in tos_vals if 0.2 <= t < 0.5)
    violated  = sum(1 for t in tos_vals if t < 0.2)
    # Approximate P1/P2/P4/P6/P7 based on available numeric data
    env_data_ok = any([raw.scope1, raw.scope2, raw.renewable_energy, raw.water_withdrawal])
    if env_data_ok:
        compliant += 2  # P6 (env) + P1 (basic)
        partial   += 1  # P4 (governance), P7 (public advocacy)
    else:
        partial += 2
        violated += 1
    return {"compliant": min(9, compliant), "partial": min(9 - compliant, partial),
            "violated": violated}


# ---------------------------------------------------------------------------
# Full pipeline — score_all_companies
# ---------------------------------------------------------------------------

def score_all_companies() -> list[dict]:
    """Load all BRSR CSVs, compute ESG scores, return list of company dicts."""
    csv_paths = list(_CLEAN_DIR.glob("*_clean.csv"))
    print(f"[scoring] Loading {len(csv_paths)} companies…")

    # Step 1: Extract raw data in parallel
    raws: list[_RawCompany] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_load_and_extract, p): p for p in csv_paths}
        done = 0
        for fut in as_completed(futures):
            done += 1
            if done % 100 == 0:
                print(f"[scoring]   {done}/{len(csv_paths)} processed…")
            result = fut.result()
            if result is not None:
                raws.append(result)

    print(f"[scoring] Extracted {len(raws)} companies. Computing scores…")

    # Step 2: Compute raw env metrics per company
    env_metrics: list[dict] = [_compute_env_raw(r) for r in raws]

    # Step 3: Sector groups for normalization
    sectors: dict[str, list[int]] = {}
    for i, r in enumerate(raws):
        sectors.setdefault(r.sector, []).append(i)

    # Step 4: Compute sector-level min/max for env and social
    sector_env_stats:    dict[str, dict] = {}
    sector_social_stats: dict[str, dict] = {}

    for sector, idxs in sectors.items():
        gi_vals  = [env_metrics[i]["ghg_intensity"]    for i in idxs if env_metrics[i]["ghg_intensity"] is not None]
        rp_vals  = [env_metrics[i]["renewable_pct"]    for i in idxs if env_metrics[i]["renewable_pct"] is not None]
        wi_vals  = [env_metrics[i]["water_intensity"]  for i in idxs if env_metrics[i]["water_intensity"] is not None]
        wr_vals  = [env_metrics[i]["waste_recovery_rate"] for i in idxs if env_metrics[i]["waste_recovery_rate"] is not None]

        tos_vals = [_compute_overall_tos(raws[i]) for i in idxs]

        sector_env_stats[sector] = {
            "gi_lo":  min(gi_vals, default=0), "gi_hi":  max(gi_vals, default=1),
            "rp_lo":  min(rp_vals, default=0), "rp_hi":  max(rp_vals, default=100),
            "wi_lo":  min(wi_vals, default=0), "wi_hi":  max(wi_vals, default=1),
            "wr_lo":  min(wr_vals, default=0), "wr_hi":  max(wr_vals, default=100),
        }
        sector_social_stats[sector] = {
            "tos_lo": min(tos_vals, default=0),
            "tos_hi": max(tos_vals, default=1),
        }

    # Step 5: Build final profiles
    results: list[dict] = []
    for i, raw in enumerate(raws):
        env = env_metrics[i]
        es  = sector_env_stats[raw.sector]
        ss  = sector_social_stats[raw.sector]

        # Environmental score (0-100)
        e_ghg  = _norm_lower_better(env["ghg_intensity"],    es["gi_lo"], es["gi_hi"])
        e_ren  = _norm_higher_better(env["renewable_pct"],   es["rp_lo"], es["rp_hi"])
        e_wat  = _norm_lower_better(env["water_intensity"],  es["wi_lo"], es["wi_hi"])
        e_wst  = _norm_higher_better(env["waste_recovery_rate"], es["wr_lo"], es["wr_hi"])
        env_score = (0.35 * e_ghg + 0.30 * e_ren + 0.20 * e_wat + 0.15 * e_wst) * 100

        # Social score (0-100, via SRS inversion)
        tos = _compute_overall_tos(raw)
        tos_lo, tos_hi = ss["tos_lo"], ss["tos_hi"]
        span = tos_hi - tos_lo
        if span < 1e-9:
            srs = 50.0
        else:
            srs = (1 - (tos - tos_lo) / span) * 100
        social_score = 100.0 - srs

        # Governance score (0-100)
        gov_score = _compute_gov_score(raw)

        # Composite ESG score
        esg_score = round(0.50 * env_score + 0.35 * social_score + 0.15 * gov_score, 1)

        # Derived display values
        ghg_display     = round((env.get("ghg_total") or 0) / 1e6, 1)
        water_display   = round((raw.water_withdrawal or 0) / 1e6, 2)
        energy_display  = round((env.get("total_energy") or 0) / 1e6, 1)
        waste_display   = round((raw.waste_generated or 0) / 1000, 2)
        renew_display   = round(env.get("renewable_pct") or 0, 0)

        trend      = _compute_trend(raw)
        highlights = _compute_highlights(raw, env, esg_score)
        principles = _compute_principles(raw)

        results.append({
            "id":              raw.symbol.lower(),
            "name":            raw.name,
            "ticker":          raw.symbol,
            "sector":          raw.sector,
            "score":           esg_score,
            "grade":           _grade(esg_score),
            "ghg":             ghg_display,
            "water":           water_display,
            "energy":          energy_display,
            "waste":           waste_display,
            "renewableShare":  int(renew_display),
            "trend":           trend,
            "fy":              f"FY{raw.fy}",
            "principles":      principles,
            "highlights":      highlights,
            # Extended
            "envScore":        round(env_score, 1),
            "socialScore":     round(social_score, 1),
            "govScore":        round(gov_score, 1),
            "overallTos":      round(tos, 4),
            "srs":             round(srs, 2),
        })

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    print(f"[scoring] Done. {len(results)} companies scored.")
    return results


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

_CACHE: list[dict] | None = None


def get_companies_cached(force: bool = False) -> list[dict]:
    """Return cached company profiles, computing and saving on first call."""
    global _CACHE
    if _CACHE is not None and not force:
        return _CACHE

    if not force and _CACHE_FILE.exists():
        try:
            with open(_CACHE_FILE, encoding="utf-8") as f:
                _CACHE = json.load(f)
            print(f"[scoring] Loaded {len(_CACHE)} companies from cache.")
            return _CACHE
        except Exception as e:
            print(f"[scoring] Cache read error ({e}), recomputing…")

    _CACHE = score_all_companies()
    try:
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_CACHE, f, ensure_ascii=False)
        print(f"[scoring] Cache saved to {_CACHE_FILE}")
    except Exception as e:
        print(f"[scoring] Cache save error: {e}")
    return _CACHE
