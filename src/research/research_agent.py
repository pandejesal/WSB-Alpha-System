import logging
from typing import Any

from src.research.base_search import SearchProvider
from src.utils.base_provider import LLMProvider


class ResearchAgent:
    def __init__(self, search_provider: SearchProvider, llm_provider: LLMProvider):
        self.search = search_provider
        self.llm = llm_provider
        self.logger = logging.getLogger(__name__)

    def run_research_cycle(self, topic: str) -> dict[str, Any]:
        self.logger.info(f"Starting research cycle for topic: {topic}")
        # 1. Search the internet
        results = self.search.search(topic, num_results=3)

        # 2. Fetch and read content
        context = []
        for res in results:
            content = self.search.fetch_content(res['url'])
            if content:
                context.append(f"Source: {res['title']}\nContent: {content}")

        full_context = "\n\n".join(context)

        # 3. Extract hypothesis using LLM
        prompt = f"""
        You are a senior quantitative researcher. Based on the following research context,
        extract a robust quantitative trading hypothesis. Do not invent details.
        Focus on market inefficiencies, statistical edges, and risk boundaries.

        Context:
        {full_context}
        """

        # We assume the llm provider has a generate_json method that takes a prompt and a schema
        try:
            hypothesis = self.llm.generate_json(
                prompt=prompt,
                schema={"type": "object", "properties": {"hypothesis": {"type": "string"}, "edge": {"type": "string"}}}
            )
            return hypothesis
        except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
            self.logger.error(f"Failed to generate hypothesis: {e}")
            return {}
