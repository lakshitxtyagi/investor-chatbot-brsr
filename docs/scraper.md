# BRSR Data Extraction and Organization Documentation

## Overview
This document explains how BRSR data was extracted from NSE endpoints and how it was organized into structured files for downstream analysis.

The pipeline is implemented in:
- `scraper.py` for metadata/API collection
- `data_extraction.py` for XML download, XBRL parsing, and CSV generation

## Extraction Workflow

### 1. Initial Attempt: Standard Web Scraping
The first approach used a normal scraping strategy:
- Open the public NSE pages
- Reuse browser-like headers
- Establish session cookies
- Request data through the visible website routes

This approach was inconsistent due to anti-bot/security protections on NSE-facing pages. Typical blockers included:
- Session/cookie validation requirements
- Request fingerprint checks
- Intermittent responses when endpoint access was tied to browser context

As a result, scraping directly from rendered web content was not reliable.

### 2. Discovery Through Developer Tools
During debugging in browser developer mode (Network tab), we identified a direct API endpoint used by the frontend to fetch corporate sustainability filing metadata.

Key finding:
- The metadata URL used by the frontend was accessible without strict protection in our usage context.
- Once this endpoint was identified, extraction became stable and much easier.

This removed the need for HTML parsing and allowed direct JSON retrieval.

### 3. Metadata Collection (`scraper.py`)
`scraper.py` does the following:
1. Creates a persistent `requests.Session()`.
2. Sends browser-like headers (`User-Agent`, `Referer`, etc.).
3. Hits NSE base URL first to warm up session cookies.
4. Calls the discovered metadata API endpoint:
   - `https://www.nseindia.com/api/corporate-bussiness-sustainabilitiy`
5. Saves response JSON to:
   - `nse_brsr_data.json`

This JSON contains listing-level metadata, including links to XBRL files.

### 4. XML/XBRL Download + Parsing (`data_extraction.py`)
`data_extraction.py` consumes `nse_brsr_data.json` and processes each record:
1. Reads records from JSON (supports nested/wrapped structures).
2. Creates output folders:
   - `brsr-data/xml/`
   - `brsr-data/csv/`
3. For each company filing:
   - Builds XML destination filename from symbol + FY
   - Downloads XBRL XML (proxy endpoint first, direct URL fallback)
4. Parses XML facts and context:
   - Extracts element name, value, contextRef, period, dimensions, unit, decimals
5. Writes one CSV per filing to `brsr-data/csv/`.
6. Appends all rows to one consolidated file:
   - `brsr-data/brsr_master.csv`

## Data Organization

### Input
- `nse_brsr_data.json`: metadata records fetched from NSE API.

### Intermediate
- `brsr-data/xml/*.xml`: downloaded XBRL XML filings.

### Final Structured Output
- `brsr-data/csv/*.csv`: filing-level CSVs (one per company/FY).
- `brsr-data/brsr_master.csv`: combined master table across all processed filings.

### CSV Schema (Extracted Facts)
Core fields produced by parsing:
- `symbol`
- `companyName`
- `fyFrom`
- `fyTo`
- `submissionDate`
- `element`
- `value`
- `contextRef`
- `period`
- `dimensions`
- `unit`
- `decimals`

## Reliability Notes
- A startup session and realistic headers are still used for request stability.
- Download logic includes fallback (proxy -> direct).
- Files already downloaded are skipped to support resumable execution.
- `START_INDEX` in `data_extraction.py` allows continuation from a chosen record index.

## Important Compliance Note
Even when an endpoint appears unprotected, usage should still follow:
- NSE terms of use
- robots and platform policies
- legal and institutional data-governance requirements

This project used endpoint discovery only to improve extraction reliability and avoid brittle page-level scraping.
