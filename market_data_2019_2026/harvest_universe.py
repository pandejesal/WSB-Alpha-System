import os
import time
import requests
import csv
import json
from datetime import datetime

base_dir = r"C:\Users\DELL\Documents\Default Project\WSB-Alpha-System-latest"
market_dir = os.path.join(base_dir, "market_data_2019_2026", "institutions")
runlog_dir = os.path.join(base_dir, "launch", "runlog")
state_path = os.path.join(runlog_dir, "B.state.json")

headers = {
    "User-Agent": "WSBAlphaSystemAdmin AdminContact@wsbalphasystem.com"
}

def update_state(patch):
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            st = json.load(f)
        st.update(patch)
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(st, f, indent=2)
    except Exception as e:
        print("Error updating state:", e)

# Quarters from 2019Q1 to 2026Q2
quarters = [
    ("2019-01-01", "2019-03-31", "2019Q1"),
    ("2019-04-01", "2019-06-30", "2019Q2"),
    ("2019-07-01", "2019-09-30", "2019Q3"),
    ("2019-10-01", "2019-12-31", "2019Q4"),
    ("2020-01-01", "2020-03-31", "2020Q1"),
    ("2020-04-01", "2020-06-30", "2020Q2"),
    ("2020-07-01", "2020-09-30", "2020Q3"),
    ("2020-10-01", "2020-12-31", "2020Q4"),
    ("2021-01-01", "2021-03-31", "2021Q1"),
    ("2021-04-01", "2021-06-30", "2021Q2"),
    ("2021-07-01", "2021-09-30", "2021Q3"),
    ("2021-10-01", "2021-12-31", "2021Q4"),
    ("2022-01-01", "2022-03-31", "2022Q1"),
    ("2022-04-01", "2022-06-30", "2022Q2"),
    ("2022-07-01", "2022-09-30", "2022Q3"),
    ("2022-10-01", "2022-12-31", "2022Q4"),
    ("2023-01-01", "2023-03-31", "2023Q1"),
    ("2023-04-01", "2023-06-30", "2023Q2"),
    ("2023-07-01", "2023-09-30", "2023Q3"),
    ("2023-10-01", "2023-12-31", "2023Q4"),
    ("2024-01-01", "2024-03-31", "2024Q1"),
    ("2024-04-01", "2024-06-30", "2024Q2"),
    ("2024-07-01", "2024-09-30", "2024Q3"),
    ("2024-10-01", "2024-12-31", "2024Q4"),
    ("2025-01-01", "2025-03-31", "2025Q1"),
    ("2025-04-01", "2025-06-30", "2025Q2"),
    ("2025-07-01", "2025-09-30", "2025Q3"),
    ("2025-10-01", "2025-12-31", "2025Q4"),
    ("2026-01-01", "2026-03-31", "2026Q1"),
    ("2026-04-01", "2026-06-30", "2026Q2"),
]

universe_csv = os.path.join(market_dir, "13f_universe_index.csv")
print("Starting 13F Universe Index harvest...")

rows = []
for startdt, enddt, qlabel in quarters:
    print(f"Harvesting quarter {qlabel} ({startdt} to {enddt})...")
    # 13F-HR count
    hr_url = f"https://efts.sec.gov/LATEST/search-index?q=%22%3C13F-HR%3E%22&forms=13F-HR&dateRange=custom&startdt={startdt}&enddt={enddt}&output=json"
    hr_count = 0
    try:
        r = requests.get(hr_url, headers=headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            hr_count = data.get("hits", {}).get("total", {}).get("value", data.get("hits", {}).get("total", 0))
        time.sleep(3.2)
    except Exception as e:
        print(f"Error fetching 13F-HR for {qlabel}: {e}")
        time.sleep(3.2)

    # 13F-NT count & top new filers
    nt_url = f"https://efts.sec.gov/LATEST/search-index?q=%22%3C13F-NT%3E%22&forms=13F-NT&dateRange=custom&startdt={startdt}&enddt={enddt}&output=json"
    nt_count = 0
    top_new = []
    try:
        r = requests.get(nt_url, headers=headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            total_field = data.get("hits", {}).get("total", 0)
            if isinstance(total_field, dict):
                nt_count = total_field.get("value", 0)
            else:
                nt_count = total_field
            hits_list = data.get("hits", {}).get("hits", [])
            for hit in hits_list[:25]:
                src = hit.get("_source", {})
                cik = src.get("cik", "")
                name = src.get("display_names", [src.get("biz_name", "")])
                if isinstance(name, list) and name:
                    name = name[0]
                elif not isinstance(name, str):
                    name = str(name)
                filing_date = src.get("file_date", "")
                top_new.append({"cik": cik, "name": name, "date": filing_date})
        time.sleep(3.2)
    except Exception as e:
        print(f"Error fetching 13F-NT for {qlabel}: {e}")
        time.sleep(3.2)

    rows.append({
        "quarter": qlabel,
        "filing_13f_hr_count": hr_count,
        "filing_13f_nt_count": nt_count,
        "top_new_filers_json": json.dumps(top_new)
    })
    update_state({"universeQuarters": len(rows)})

with open(universe_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["quarter", "filing_13f_hr_count", "filing_13f_nt_count", "top_new_filers_json"])
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

print("13F Universe Index saved to", universe_csv)
update_state({"artifacts": [universe_csv]})
