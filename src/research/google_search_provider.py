import requests
from bs4 import BeautifulSoup
from src.research.base_search import SearchProvider
from typing import List, Dict
from duckduckgo_search import DDGS
import logging

class DDGSearchProvider(SearchProvider):
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        self.logger.info(f"Searching DuckDuckGo for: {query}")
        results = []
        try:
            with DDGS() as ddgs:
                ddgs_gen = ddgs.text(query, max_results=num_results)
                for r in ddgs_gen:
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", "")
                    })
        except Exception as e:
            self.logger.error(f"DDG Search failed: {e}")
        return results

    def fetch_content(self, url: str) -> str:
        if not url:
            return ""
        try:
            self.logger.info(f"Fetching content from: {url}")
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.content, 'html.parser')
            # Extract basic text
            text = ' '.join(p.get_text() for p in soup.find_all('p'))
            return text[:5000] # Limit to avoid massive tokens
        except Exception as e:
            self.logger.error(f"Failed to fetch content from {url}: {e}")
            return ""
