# BRSR Data Preprocessing Documentation

## Overview
This document describes the preprocessing and quality-check workflow implemented in the notebook [data_preprocessing.ipynb](data_preprocessing.ipynb).

The pipeline processes raw BRSR CSV files and produces clean copies plus a quality report without dropping data rows.

## Objective
The preprocessing step is designed to:
- Validate schema consistency across all raw files.
- Detect missing values in critical fields.
- Flag unreadable or corrupted CSV files.
- Check filing-level period consistency.
- Preserve all original rows while standardizing output generation.

## Input and Output

### Input
- Raw filing CSVs from: [brsr-data/csv](brsr-data/csv)
- Expected source: one CSV per company filing extracted from XBRL.

### Output
- Cleaned copies in: [brsr-data/clean](brsr-data/clean)
- File naming pattern: `original_name_clean.csv`
- Quality summary report: [brsr-data/clean/quality_report.csv](brsr-data/clean/quality_report.csv)

## Expected Schema
The pipeline validates incoming columns (case-insensitive) against this expected set:
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

Critical fields for null checks:
- `symbol`
- `element`
- `value`

## Processing Logic

### 1. File Discovery
- Lists all `.csv` files in [brsr-data/csv](brsr-data/csv).
- Processes files in sorted order for deterministic runs.

### 2. Safe CSV Read
For each file, the notebook attempts to read with fallback encodings:
1. `utf-8`
2. `latin-1`
3. `cp1252`

If all fail, the file is logged as failed (`FAILED_UNREADABLE` or `FAILED_CORRUPT`) and processing continues.

### 3. Schema Check
- Compares actual columns vs expected columns (lowercase normalization).
- Logs:
  - `schema_ok`
  - `missing_columns`
  - `extra_columns`

### 4. Null Check
Counts null values in critical fields:
- `null_symbol`
- `null_element`
- `null_value`

### 5. Period Consistency Check
- Extracts distinct non-blank values from `period`.
- Treats placeholders like `""`, `"to"`, and `" to "` as ignorable.
- A file is considered consistent if there is at most one unique valid period.

### 6. Status Assignment
Each file gets one status:
- `OK`: schema valid, no critical null issues, and period consistent.
- `WARNING`: schema valid but has null issues and/or period inconsistency.
- `SCHEMA_ERROR`: missing expected columns.
- `FAILED_*`: unreadable/corrupt file handling failures.

### 7. Data Preservation and Output
- The notebook writes each processed DataFrame to [brsr-data/clean](brsr-data/clean).
- No row-level filtering/removal is performed in this stage.

### 8. Quality Report
All per-file logs are combined into [brsr-data/clean/quality_report.csv](brsr-data/clean/quality_report.csv), including:
- Read status
- Row counts
- Schema diagnostics
- Null metrics
- Period diagnostics
- Error details (if any)

## Summary Metrics Printed
At the end of execution, the notebook prints:
- Total files processed
- Count of `OK`, `WARNING`, `SCHEMA_ERROR`
- Total `FAILED*` files
- Number of period consistency issues
- Output locations

## Optional Inspection Block
The notebook includes an optional inspection cell that displays non-OK files for quick debugging and triage.

## How to Run
1. Ensure raw files exist in [brsr-data/csv](brsr-data/csv).
2. Open [data_preprocessing.ipynb](data_preprocessing.ipynb).
3. Run all cells in order.
4. Check outputs in [brsr-data/clean](brsr-data/clean).
5. Review [brsr-data/clean/quality_report.csv](brsr-data/clean/quality_report.csv).

## Notes
- This stage is quality validation and organization, not heavy transformation.
- Because rows are preserved, this output is suitable for downstream cleaning, normalization, or modeling decisions with full traceability.
