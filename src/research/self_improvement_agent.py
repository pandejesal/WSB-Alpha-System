import os
import re
import time
from datetime import datetime

from google import genai

from src.backtest.validation import (
    load_base_data,
    run_in_sample_test,
    run_walk_forward_test,
)


def read_logs():
    try:
        # In a real GH Action, the paper_trading_logs branch is fetched and available or checked out.
        # But we just use git to fetch it and read the latest log.
        import subprocess
        result = subprocess.run(["git", "show", "origin/paper_trading_logs:paper_trading_logs/latest_execution.log"], capture_output=True, text=True)  # noqa: PLW1510 - Implicit check=False is acceptable
        if result.returncode == 0:
            return result.stdout
        else:
            return "No recent trades found in paper_trading_logs/latest_execution.log"
    except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
        return f"Error reading logs: {e}"

def update_file(filename, old_str, new_str):
    with open(filename, 'r') as f:
        content = f.read()

    if old_str not in content:
        print(f"Warning: '{old_str}' not found in {filename}")
        return False

    if len(old_str) <= 12:
        print(f"Error: old_str must be longer than 12 characters to prevent accidental replacements. Got: '{old_str}'")
        return False

    if content.count(old_str) > 1:
        print(f"Error: '{old_str}' appears multiple times in {filename}. Please provide a more specific string.")
        return False

    content = content.replace(old_str, new_str, 1)

    with open(filename, 'w') as f:
        f.write(content)

    return True

def call_gemini_with_retry(client, prompt):
    models = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-2.0-flash", "gemini-3.5-flash-lite"]
    backoffs = [2, 4, 8]

    for model in models:
        for attempt in range(1, 4):
            print(f"Trying {model} (attempt {attempt}/3)...")
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt
                )
                print("Success!")
                return response.text
            except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
                error_msg = str(e)
                if '503' in error_msg or '429' in error_msg:
                    error_type = '503' if '503' in error_msg else '429'
                    if attempt < 3:
                        sleep_time = backoffs[attempt - 1]
                        print(f"{error_type} error, retrying in {sleep_time}s...")
                        time.sleep(sleep_time)
                    else:
                        print(f"{error_type} error, moving to next model...")
                else:
                    print(f"Other error: {e}, moving to next model...")
                    break

    return None

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("No GEMINI_API_KEY found, skipping self improvement.")
        return

    client = genai.Client(api_key=api_key)


    logs = read_logs()

    with open('src/backtest/run_historic_backtest.py', 'r') as f:
        _ = f.read()

    try:
        with open('self_improvement_log.md', 'r') as f:
            history = f.read()
    except FileNotFoundError:
        history = ""

    prompt = f"""
    You are an automated algorithmic trading quant. Your goal is to propose EXACTLY ONE parameter change to the strategy in `src/backtest/run_historic_backtest.py`.

    Rules:
    - Change only one parameter (e.g. RSI threshold, EMA span, Volatility limit).
    - Provide the exact old string to replace, and the exact new string. You MUST provide at least one full, unique line of code (e.g., df['EMA'] = df['Close'].ewm(span=20).mean()) to avoid accidental partial replacements. The `old_code` must be longer than 12 characters and exist exactly once in the file.
    - Do NOT modify position sizing limits or Phase 4 risk configurations.
    - Use the scientific method based on past logs.

    Current Logs:
    {logs}

    Past History:
    {history}

    Respond in JSON format:
    {{
        "hypothesis": "Your reasoning here.",
        "file": "src/backtest/run_historic_backtest.py",
        "old_code": "exact string to replace",
        "new_code": "exact replacement string"
    }}
    """

    try:
        response_text = call_gemini_with_retry(client, prompt)
        if response_text is None:
            print("All Gemini models unavailable after retries. Skipping this cycle.")
            return

        # Parse JSON from response
        import json
        match = re.search(r'\{.*?\}', response_text, re.DOTALL)
        if match:
            data = json.loads(match.group(0))

            # Make sure it only modifies the target file
            if data['file'] != 'src/backtest/run_historic_backtest.py':
                print(f"Agent tried to modify disallowed file: {data['file']}. Blocking.")
                return

            success = update_file(data['file'], data['old_code'], data['new_code'])

            if success:
                print("Applied change. Running validation harness...")
                try:
                    posts_df, stock_dfs, spy_close = load_base_data()
                    is_result = run_in_sample_test(posts_df, stock_dfs, spy_close)
                    is_pval = is_result[4]  # p_value is the 5th return value
                    in_sample_passed = is_pval <= 0.01

                    if in_sample_passed:
                        wf_result = run_walk_forward_test(posts_df, stock_dfs, spy_close)
                        wf_pval = wf_result[4]
                        passed = wf_pval <= 0.05
                    else:
                        passed = False
                except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
                    print(f"Validation harness crashed: {e}")
                    passed = False

                log_entry = f"\n## {datetime.now().strftime('%Y-%m-%d')}\n"  # noqa: DTZ005 - Timezone not critical for this usage
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
    except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
        print(f"Error calling Gemini: {e}")

if __name__ == "__main__":
    main()
