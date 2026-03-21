# investor-chatbot-brsr

## Overview
Extracts BRSR (Business Responsibility and Sustainability Reports) data from NSE. Downloads XBRL XML files and converts them to CSV format for analysis.

## Architecture & Process
- **Input**: Reads company metadata from `nse_brsr_data.json`
- **Download**: Fetches XBRL XML files from NSE for each company
- **Parse**: Extracts facts, contexts, units, and dimensions from XBRL
- **Output**: Generates CSV files with structured data

## Output Structure
```
brsr-data/
├── xml/              # Downloaded XBRL files by company
├── csv/              # Individual company CSVs
└── brsr_master.csv   # Combined dataset (all companies)
```