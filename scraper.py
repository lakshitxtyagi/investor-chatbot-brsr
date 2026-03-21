import requests
import json

# Base URLs
base_url = "https://www.nseindia.com"
api_url = "https://www.nseindia.com/api/corporate-bussiness-sustainabilitiy"

# Create a session to persist cookies
session = requests.Session()

# Headers to mimic a real browser
headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-bussiness-sustainabilitiy-reports",
    "Connection": "keep-alive",
}

# Step 1: Get cookies by visiting NSE homepage
session.get(base_url, headers=headers)

# Step 2: Call API
response = session.get(api_url, headers=headers)

# Step 3: Check response
if response.status_code == 200:
    data = response.json()

    # Save to file
    with open("nse_brsr_data.json", "w") as f:
        json.dump(data, f, indent=4)

    print("Data saved successfully!")
else:
    print(f"Failed! Status Code: {response.status_code}")