with open("run_historic_backtest.py", "r") as f:
    content = f.read()

# Remove duplicate functions and import them
import_str = "from indicators import compute_indicators, compute_regime_returns\n"
if "from indicators import" not in content:
    content = content.replace("import matplotlib.pyplot as plt", "import matplotlib.pyplot as plt\n" + import_str)

import re

# Remove compute_indicators
content = re.sub(r'def compute_indicators\(df\):.*?return df', '', content, flags=re.DOTALL)
# Remove compute_regime_returns
content = re.sub(r'def compute_regime_returns\(ind_df.*?return regime_stock_ret, regime_spy_ret', '', content, flags=re.DOTALL)

with open("run_historic_backtest.py", "w") as f:
    f.write(content)
