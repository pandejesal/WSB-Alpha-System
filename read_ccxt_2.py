with open("src/execution/ccxt_broker.py", "r") as f:
    lines = f.readlines()
    for i, line in enumerate(lines):
        print(f"{i}: {line.rstrip()}")
