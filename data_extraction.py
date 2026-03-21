"""
NSE BRSR XML Downloader & CSV Converter
========================================
Reads nse_brsr_data.json, downloads each XML, parses XBRL, saves CSVs.

INSTALL:  pip install requests
RUN:      python download_brsr.py  (same folder as nse_brsr_data.json)
"""

import re
import csv
import json
import time
import logging
import requests
from pathlib import Path
from urllib.parse import quote
import xml.etree.ElementTree as ET

# ── Config ─────────────────────────────────────────────────────────────────────
JSON_FILE      = Path("nse_brsr_data.json")
OUTPUT_DIR     = Path("brsr-data")
XML_DIR        = OUTPUT_DIR / "xml"
CSV_DIR        = OUTPUT_DIR / "csv"
DOWNLOAD_DELAY = 1.0
START_INDEX = 1  # Change to 594 to resume from file 594 # Change to 594 to resume from file 594, or any desired starting index

BASE_URL    = "https://www.nseindia.com"
LISTING_URL = f"{BASE_URL}/companies-listing/corporate-filings-bussiness-sustainabilitiy-reports"
PROXY_URL   = f"{BASE_URL}/api/download_xbrl"

HEADERS = {
    "User-Agent":      "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "Accept":          "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Referer":         LISTING_URL,
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)


# ── Load JSON (handles any nesting) ───────────────────────────────────────────

def load_records(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    # Could be: list of dicts, a dict with a key, or a JSON string inside a string
    if isinstance(raw, list):
        # Make sure elements are dicts, not strings
        if raw and isinstance(raw[0], dict):
            return raw
        # Possibly list of JSON strings
        result = []
        for item in raw:
            if isinstance(item, str):
                result.append(json.loads(item))
            elif isinstance(item, dict):
                result.append(item)
        return result
    elif isinstance(raw, dict):
        # Wrapped: {"data": [...]} or {"records": [...]}
        for key in ("data", "records", "brsr", "result"):
            if key in raw and isinstance(raw[key], list):
                return raw[key]
        # Single record wrapped as dict
        if "symbol" in raw:
            return [raw]
    elif isinstance(raw, str):
        return load_records_from_string(raw)
    return []

def load_records_from_string(s: str) -> list[dict]:
    parsed = json.loads(s)
    return load_records_from_value(parsed)

def load_records_from_value(v) -> list[dict]:
    if isinstance(v, list) and v and isinstance(v[0], dict):
        return v
    if isinstance(v, dict) and "symbol" in v:
        return [v]
    return []


# ── Session ────────────────────────────────────────────────────────────────────

def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    log.info("Bootstrapping NSE session ...")
    try:
        session.get(BASE_URL, timeout=20)
        time.sleep(1)
        session.get(LISTING_URL, timeout=20)
        log.info("  Cookies: %s", list(session.cookies.keys()))
        time.sleep(2)
    except Exception as e:
        log.warning("  Session error: %s", e)
    return session


# ── Download XML ───────────────────────────────────────────────────────────────

def download_xml(session: requests.Session, xml_url: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 100:
        log.info("  Already downloaded: %s", dest.name)
        return True

    encoded = quote(f'"{xml_url}"', safe="")
    proxy   = f"{PROXY_URL}?fileUrl={encoded}"

    for url, label in [(proxy, "proxy"), (xml_url, "direct")]:
        try:
            r = session.get(url, timeout=60, stream=True)
            r.raise_for_status()
            content = b"".join(r.iter_content(chunk_size=65536))
            if content.lstrip()[:1] not in (b"<", b"\xef"):
                continue
            dest.write_bytes(content)
            log.info("  ✓ [%s] %s  (%.1f KB)", label, dest.name, dest.stat().st_size / 1024)
            return True
        except Exception as e:
            log.warning("  ✗ [%s] %s", label, e)

    return False


# ── Parse XBRL → rows ─────────────────────────────────────────────────────────

def strip_ns(tag: str) -> str:
    return re.sub(r"\{[^}]+\}", "", tag)

def parse_xbrl(xml_path: Path, meta: dict) -> list[dict]:
    rows = []
    base = {
        "symbol":         meta.get("symbol", ""),
        "companyName":    meta.get("companyName", ""),
        "fyFrom":         meta.get("fyFrom", ""),
        "fyTo":           meta.get("fyTo", ""),
        "submissionDate": meta.get("submissionDate", ""),
    }

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError as e:
        log.error("  XML parse error: %s", e)
        return rows

    # Build context map
    context_map = {}
    for elem in root.iter():
        if strip_ns(elem.tag) == "context":
            ctx_id, info = elem.attrib.get("id", ""), {}
            for c in elem.iter():
                t = strip_ns(c.tag)
                if t == "instant":       info["period"] = c.text or ""
                elif t == "startDate":   info["startDate"] = c.text or ""
                elif t == "endDate":     info["endDate"] = c.text or ""
                elif t == "explicitMember":
                    axis = strip_ns(c.attrib.get("dimension", ""))
                    info.setdefault("dimensions", []).append(f"{axis}={strip_ns(c.text or '')}")
            if "dimensions" in info:
                info["dimensions"] = "; ".join(info["dimensions"])
            context_map[ctx_id] = info

    # Build unit map
    unit_map = {}
    for elem in root.iter():
        if strip_ns(elem.tag) == "unit":
            uid = elem.attrib.get("id", "")
            meas = next((strip_ns(c.text or "") for c in elem.iter() if strip_ns(c.tag) == "measure"), "")
            unit_map[uid] = meas.split(":")[-1] if ":" in meas else meas

    # Extract facts
    skip = {"xbrl","schemaRef","context","unit","entity","identifier","period",
            "segment","explicitMember","instant","startDate","endDate",
            "measure","divide","unitNumerator","unitDenominator"}

    for elem in root.iter():
        tag   = strip_ns(elem.tag)
        if tag in skip: continue
        value = (elem.text or "").strip()
        if not value: continue

        ctx_ref  = elem.attrib.get("contextRef", "")
        unit_ref = elem.attrib.get("unitRef", "")
        ctx      = context_map.get(ctx_ref, {})

        rows.append({
            **base,
            "element":    tag,
            "value":      value,
            "contextRef": ctx_ref,
            "period":     ctx.get("period") or f"{ctx.get('startDate','')} to {ctx.get('endDate','')}",
            "dimensions": ctx.get("dimensions", ""),
            "unit":       unit_map.get(unit_ref, unit_ref),
            "decimals":   elem.attrib.get("decimals", ""),
        })

    return rows


# ── Save CSV ───────────────────────────────────────────────────────────────────

FIELDS = ["symbol","companyName","fyFrom","fyTo","submissionDate",
          "element","value","contextRef","period","dimensions","unit","decimals"]

def save_csv(rows: list[dict], path: Path):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    log.info("  Saved %s (%d rows)", path.name, len(rows))


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    if not JSON_FILE.exists():
        log.error("Cannot find %s", JSON_FILE)
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    XML_DIR.mkdir(parents=True, exist_ok=True)
    CSV_DIR.mkdir(parents=True, exist_ok=True)

    records = load_records(JSON_FILE)
    if not records:
        log.error("Could not parse records from %s. Check the JSON structure.", JSON_FILE)
        return
    log.info("Loaded %d records from %s", len(records), JSON_FILE)

    session  = create_session()
    all_rows = []
    dl_ok = dl_fail = parse_ok = parse_fail = 0

    for i, rec in enumerate(records, 1):
        # Skip records before START_INDEX
        if i < START_INDEX:
            continue
        symbol  = rec.get("symbol", f"UNK_{i}")
        company = rec.get("companyName", symbol)
        xml_url = rec.get("xbrlFile", "").strip()
        fy      = f"{rec.get('fyFrom','')}_{rec.get('fyTo','')}"
        safe    = re.sub(r'[\\/*?:"<>|]', "_", symbol)

        log.info("[%d/%d] %s  (%s)", i, len(records), company[:55], fy)

        if not xml_url:
            log.warning("  No XML URL — skipping.")
            dl_fail += 1
            continue

        xml_path = XML_DIR / f"{safe}_{fy}.xml"
        if not download_xml(session, xml_url, xml_path):
            dl_fail += 1
            time.sleep(DOWNLOAD_DELAY)
            continue
        dl_ok += 1

        rows = parse_xbrl(xml_path, rec)
        if rows:
            parse_ok += 1
            all_rows.extend(rows)
            save_csv(rows, CSV_DIR / f"{safe}_{fy}.csv")
        else:
            parse_fail += 1
            log.warning("  No rows extracted.")

        time.sleep(DOWNLOAD_DELAY)

    if all_rows:
        master = OUTPUT_DIR / "brsr_master.csv"
        save_csv(all_rows, master)
        log.info("Master CSV → %s  (%d total rows)", master, len(all_rows))

    log.info("")
    log.info("=" * 50)
    log.info("  Records    : %d", len(records))
    log.info("  XML OK     : %d  |  failed: %d", dl_ok, dl_fail)
    log.info("  Parsed OK  : %d  |  failed: %d", parse_ok, parse_fail)
    log.info("  Total rows : %d", len(all_rows))
    log.info("  Output     : %s", OUTPUT_DIR.resolve())
    log.info("=" * 50)

if __name__ == "__main__":
    main()