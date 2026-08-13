import json

src = r"archive/run-20260810-1420/market_data_2019_2026/news/raw/g_2024Q3.jsonl"

n_lines = 0
with open(src, encoding="utf-8") as f:
    for line in f:
        n_lines += 1
        if n_lines <= 3:
            obj = json.loads(line)
            print(json.dumps(obj, indent=2)[:1200])
print("---")
print("lines:", n_lines)
