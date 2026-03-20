# Dataset Information

## Overview
This project uses Business Responsibility and Sustainability Reporting (BRSR) data for ~1000 Indian companies across two financial years (~2000 Excel files).

Due to GitHub size and performance constraints, the dataset is hosted externally.

---

## Dataset Access

### 1. Processed Excel Files (Primary Dataset)
Google Drive Link:
https://drive.google.com/drive/folders/10seAgCKtnM0iqmNFwn27YUDFUDYD9VY8?usp=drive_link

---

### 2. Official Source (NSE India)
BRSR Filings:
https://www.nseindia.com/companies-listing/corporate-filings-bussiness-sustainabilitiy-reports

---

## How to Use

1. Download the dataset from the Google Drive link
2. Extract (if zipped)
3. Place the folder in the project root as:

Dataset/Excel Files/

---

## Notes
- Dataset contains 2000+ `.xlsx` files (~200 MB)
- Not included in repository to maintain performance and usability
- All preprocessing scripts assume this directory structure

---

## Data Description

Each Excel file contains:
- `elementName`: BRSR disclosure field
- `factValue`: Company response (text/numeric)

The preprocessing pipeline extracts:
- Company Name
- Year
- Element Name
- Text Disclosure (Fact Value)
