import sys

sys.path.insert(0, r"market_data_2019_2026\tools")
from C_causation import gdelt_artlist
from datetime import datetime

res = gdelt_artlist("AAPL", "Apple Inc.", datetime(2022, 1, 1), datetime(2022, 1, 31, 23, 59, 59))
if res is None:
    print("RESULT: FAILED (None)")
else:
    print("RESULT: OK count =", len(res))
    for a in res[:3]:
        print("-", (a.get("title") or "")[:80], "|", a.get("domain"), "|", a.get("datetime"))