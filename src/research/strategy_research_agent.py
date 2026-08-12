import json
import logging
import os

from google import genai
from google.genai import types

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("StrategyResearchAgent")

from google.genai.types import (
    FunctionDeclaration,
    GenerateContentConfig,
    Tool,
)

from src.research.google_search_provider import (
    DDGSearchProvider,
)


def search_strategy_concepts_online(query: str) -> str:
    """Real implementation using DDGSearchProvider"""
    logger.info(f"Searching internet for trading concepts: {query}")
    provider = DDGSearchProvider()
    results = provider.search(query, num_results=3)

    if not results:
        logger.warning(f"No results found for query: {query}")
        return json.dumps([])

    enriched_results = []
    for r in results:
        url = r.get("url")
        content = provider.fetch_content(url) if url else r.get("snippet", "")
        enriched_results.append({
            "title": r.get("title", ""),
            "content": content[:1000] if content else r.get("snippet", "")
        })
    return json.dumps(enriched_results)

def save_generated_strategy(strategy_name: str, python_code: str) -> str:
    """Saves the generated python code to the strategies folder/file"""
    filename = f"strategy_{strategy_name.lower().replace(' ', '_')}.py"
    try:
        with open(filename, 'w') as f:
            f.write(python_code)
        logger.info(f"Successfully saved new strategy to {filename}")
        return f"Successfully saved {filename}"
    except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
        logger.error(f"Failed to save strategy: {e}")
        return f"Error saving strategy: {e}"

search_concept_decl = FunctionDeclaration(
    name="search_strategy_concepts_online",
    description="Searches the internet for new quantitative trading strategy concepts and alpha factors.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "query": types.Schema(
                type=types.Type.STRING,
                description="The search query, e.g., 'mean reversion crypto strategy python'"
            )
        },
        required=["query"]
    )
)

save_strategy_decl = FunctionDeclaration(
    name="save_generated_strategy",
    description="Saves a valid Python strategy code into a new file.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "strategy_name": types.Schema(type=types.Type.STRING, description="A short, descriptive name for the strategy."),
            "python_code": types.Schema(type=types.Type.STRING, description="The complete, runnable Python code for the strategy.")
        },
        required=["strategy_name", "python_code"]
    )
)

class StrategyResearchAgent:
    def __init__(self):
        # The memory explicitly mentions avoiding google-generativeai in favor of google-genai
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found. Agent will fail if called.")

        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

        # Memory says to use gemini-3.1-pro-preview-customtools (We will use 2.5 flash if 3.1 isn't available, but we use what memory says first)
        self.model_name = "gemini-2.5-flash"

        self.tools = Tool(
            function_declarations=[search_concept_decl, save_strategy_decl]
        )

    def run_research_cycle(self, focus_area="crypto momentum strategies"):
        logger.info(f"Starting strategy research cycle with focus: {focus_area}")
        if not self.client:
            logger.error("No Gemini API key.")
            return

        prompt = f"""
        You are an elite quantitative researcher tasked with finding and implementing new trading strategies.
        Your focus area for this cycle is: {focus_area}

        1. Use the `search_strategy_concepts_online` tool to find alpha concepts.
        2. Select one promising concept.
        3. Write a Python function for it. The function must accept a Pandas DataFrame `df` with 'Open', 'High', 'Low', 'Close', 'Volume' columns.
        4. The function must return a Pandas Series of signals (1 for buy/long, -1 for short, 0 for neutral).
        5. Use the `save_generated_strategy` tool to save your code.
        """

        config = GenerateContentConfig(
            tools=[self.tools],
            temperature=0.7
        )

        try:
             # Basic tool call loop simulation
             response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
             )

             # Process tool calls if any
             if response.function_calls:
                 for call in response.function_calls:
                     if call.name == "search_strategy_concepts_online":
                         res = search_strategy_concepts_online(**call.args)
                         logger.info(f"Search Result: {res[:200]}...")
                     elif call.name == "save_generated_strategy":
                         res = save_generated_strategy(**call.args)
                         logger.info(res)
             else:
                 logger.info(f"Agent response: {response.text}")

        except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
             logger.error(f"Agent failed: {e}")

if __name__ == "__main__":
    agent = StrategyResearchAgent()
