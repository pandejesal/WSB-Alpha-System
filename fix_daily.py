import re

with open('src/ops/daily.py', 'r') as f:
    content = f.read()

content = content.replace(
    '                    for k in weights:\n                        weights[k] = round(inv_vol[k] / total_inv_vol, 6)',
    '                    for k in weights.keys():\n                        weights[k] = round(inv_vol[k] / total_inv_vol, 6)'
)

content = content.replace(
    '                 for k in weights:\n                     if k != "btc_vol_target_sma100":\n                         weights[k] = round(weights[k] * scale, 6)',
    '                 for k, v in weights.items():\n                     if k != "btc_vol_target_sma100":\n                         weights[k] = round(v * scale, 6)'
)

with open('src/ops/daily.py', 'w') as f:
    f.write(content)
