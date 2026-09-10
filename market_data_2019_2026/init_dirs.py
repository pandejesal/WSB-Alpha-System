import json
import os
import time
from datetime import datetime

import requests

base_dir = r"C:\Users\DELL\Documents\Default Project\WSB-Alpha-System-latest"
market_dir = os.path.join(base_dir, "market_data_2019_2026", "institutions")
fh_dir = os.path.join(market_dir, "13f")
vc_dir = os.path.join(market_dir, "vc")
runlog_dir = os.path.join(base_dir, "launch", "runlog")

for d in [market_dir, fh_dir, vc_dir, runlog_dir]:
    os.makedirs(d, exist_ok=True)

print("Directories created successfully.")
