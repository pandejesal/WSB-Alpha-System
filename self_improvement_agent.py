import os
import re
import google.generativeai as genai
from validation import run_permutation_test
from datetime import datetime


def read_logs():
    try:
        # In a real GH Action, the paper_trading_logs branch is fetched and available or checked out.
        # But we just use git to fetch it and read the latest log.
        import subprocess
        result = subprocess.run(["git", "show", "origin/paper_trading_logs:paper_trading_logs/latest_execution.log"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
        else:
            return "No recent trades found in paper_trading_logs/latest_execution.log"
    except Exception as e:
        return f"Error reading logs: {e}"

def update_file(filename, old_str, new_str):
    with open(filename, 'r') as f:
        content = f.read()

    if old_str not in content:
        print(f"Warning: '{old_str}' not found in {filename}")
        return False

    content = content.replace(old_str, new_str)

    with open(filename, 'w') as f:
        f.write(content)

    return True

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("No GEMINI_API_KEY found, skipping self improvement.")
        return

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    logs = read_logs()

    with open('run_historic_backtest.py', 'r') as f:
        _ = f.read()

    try:
        with open('self_improvement_log.md', 'r') as f:
            history = f.read()
    except FileNotFoundError:
        history = ""

    prompt = f"""
    You are an automated algorithmic trading quant. Your goal is to propose EXACTLY ONE parameter change to the strategy in `run_historic_backtest.py`.

    Rules:
    - Change only one parameter (e.g. RSI threshold, EMA span, Volatility limit).
    - Provide the exact old string to replace, and the exact new string.
    - Do NOT modify position sizing limits or Phase 4 risk configurations.
    - Use the scientific method based on past logs.

    Current Logs:
    {logs}

    Past History:
    {history}

    Respond in JSON format:
    {{
        "hypothesis": "Your reasoning here.",
        "file": "run_historic_backtest.py",
        "old_code": "exact string to replace",
        "new_code": "exact replacement string"
    }}
    """

    try:
        response = model.generate_content(prompt)
        # Parse JSON from response
        import json
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            data = json.loads(match.group(0))

            # Make sure it doesn't try to edit risk_config.py
            if 'risk_config.py' in data['file']:
                print("Agent tried to modify risk_config.py. Blocking.")
                return

            success = update_file(data['file'], data['old_code'], data['new_code'])

            if success:
                print("Applied change. Running validation harness...")
                passed = run_permutation_test()

                log_entry = f"\n## {datetime.now().strftime('%Y-%m-%d')}\n"
                log_entry += f"**Hypothesis:** {data['hypothesis']}\n"
                log_entry += f"**Change:** `{data['old_code']}` -> `{data['new_code']}`\n"
                log_entry += f"**Result:** {'PASSED' if passed else 'FAILED'}\n\n"

                with open('self_improvement_log.md', 'a') as f:
                    f.write(log_entry)

                if not passed:
                    print("Validation failed. Reverting...")
                    update_file(data['file'], data['new_code'], data['old_code']) # Revert
            else:
                print("Failed to apply change (string mismatch).")
    except Exception as e:
        print(f"Error calling Gemini: {e}")

if __name__ == "__main__":
    main()
