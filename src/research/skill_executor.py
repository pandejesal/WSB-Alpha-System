import asyncio
import os
import sqlite3
import yaml
import json
from google import genai
from google.genai import types
from src.research.agent_skills_registry import skills_tool, skills_registry

class GeminiSkillEngine:
    def __init__(self):
        # We need an API key for GenAI. Normally we'd get this from os.environ
        # The prompt says: "The user has a Google AI Pro Plan linked to AI Studio"
        self.api_key = os.environ.get("GEMINI_API_KEY", "mock_key")
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "gemini-3.1-pro-preview-customtools"
        self.cached_content = None

    def _prepare_cache_content(self) -> str:
        content_parts = []

        # 1. strategy_config.yaml
        if os.path.exists("strategy_config.yaml"):
            with open("strategy_config.yaml", "r") as f:
                yaml_content = f.read()
            content_parts.append("--- strategy_config.yaml ---\n" + yaml_content)

        # 2. trades.db (last 30 days of trades as CSV text)
        if os.path.exists("trades.db"):
            conn = sqlite3.connect("trades.db")
            # Convert last 30 days or last 50 trades to CSV text for LLM ingestion
            import pandas as pd
            df = pd.read_sql_query("SELECT * FROM trades ORDER BY entry_time DESC LIMIT 50", conn)
            conn.close()
            csv_text = df.to_csv(index=False)
            content_parts.append("\n--- trades.db (latest trades) ---\n" + csv_text)

        return "\n".join(content_parts)

    def _create_context_cache(self, system_instruction: str) -> types.CachedContent:
        print("Uploading context cache to Google AI Studio...")
        text_content = self._prepare_cache_content()

        # Using context caching via the google-genai client
        cached_content = self.client.caches.create(
            model=self.model_name,
            config=types.CreateCachedContentConfig(
                system_instruction=system_instruction,
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=text_content)]
                    )
                ],
                # 1 hour TTL
                ttl="3600s",
            )
        )
        print(f"Cache created successfully: {cached_content.name}")
        return cached_content

    async def run_optimization_loop(self, system_instruction: str, prompt: str):
        # 1. Create Cache
        try:
            self.cached_content = self._create_context_cache(system_instruction)
        except Exception as e:
            # If we don't have an API key or hit an error, we can't actually hit the cache endpoint in mock
            print(f"Warning: Failed to create cache (expected in mock environment without valid key). Error: {e}")
            return

        print("Starting optimization loop...")

        # 2. Setup the model with custom tools and the cached content
        # Note: According to google-genai, if using cached_content, we pass it in the generate_content call
        # or we might need to initialize it differently depending on exact API semantics, but usually we pass the cached content name.

        # For a chat session, we can initialize a chat and pass tools
        # The prompt requests standard intercept loop

        messages = [
            types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
        ]

        # Enforce max 5 tool calls
        max_turns = 5
        turn = 0

        while turn < max_turns:
            print(f"Turn {turn + 1}/{max_turns}...")

            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=messages,
                    config=types.GenerateContentConfig(
                        tools=[skills_tool],
                        cached_content=self.cached_content.name
                    )
                )
            except Exception as e:
                print(f"API Error during generation: {e}")
                break

            if not response.candidates:
                print("No candidates returned.")
                break

            candidate = response.candidates[0]

            # Extract text (if any) and print
            text_parts = [p.text for p in candidate.content.parts if p.text]
            if text_parts:
                print("Gemini:", " ".join(text_parts))

            # Check for function calls
            function_calls = [p.function_call for p in candidate.content.parts if p.function_call]

            if not function_calls:
                print("No function calls requested. Loop finished.")
                break

            # Append model response to history
            messages.append(candidate.content)

            # Execute function calls asynchronously (or serially in this simple loop)
            function_responses = []

            for fc in function_calls:
                func_name = fc.name
                func_args = {k: v for k, v in fc.args.items()} if fc.args else {}

                print(f"Executing tool: {func_name} with args: {func_args}")

                if func_name in skills_registry:
                    # Run the python function
                    # If it were async, we'd await it. Here they are sync.
                    # We can use asyncio.to_thread if we want true async offloading.
                    try:
                        result = await asyncio.to_thread(skills_registry[func_name], **func_args)
                    except Exception as e:
                        result = {"error": str(e)}
                else:
                    result = {"error": f"Unknown function {func_name}"}

                print(f"Tool result: {result}")

                function_responses.append(
                    types.Part.from_function_response(
                        name=func_name,
                        response=result
                    )
                )

            # Append tool responses to history as user role
            messages.append(
                types.Content(
                    role="user", # GenAI function responses are typically passed in user role parts or specialized role
                    parts=function_responses
                )
            )

            turn += 1

        if turn >= max_turns:
            print("Maximum tool calls reached. Exiting to prevent infinite loop.")

async def main():
    engine = GeminiSkillEngine()

    with open("PROMPT_ENGINEERING.md", "r") as f:
        sys_inst = f.read()

    prompt = (
        "Using your tools, first analyze the ledger's MFE and MAE. "
        "Then, formulate a hypothesis to improve the strategy's risk parameters. "
        "Run a sandbox backtest with your proposed `cvar_threshold`, `stop_loss_atr`, and `take_profit_atr`. "
        "Iterate if necessary, and output your final optimized configuration."
    )

    await engine.run_optimization_loop(system_instruction=sys_inst, prompt=prompt)

if __name__ == "__main__":
    asyncio.run(main())
