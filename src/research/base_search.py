from abc import ABC, abstractmethod
from typing import List, Dict

class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """
        Search the internet/source.
        Returns a list of dicts with keys: 'title', 'url', 'snippet'.
        """
        pass

    @abstractmethod
    def fetch_content(self, url: str) -> str:
        """
        Fetch the full text content from a given URL.
        """
        pass
