from abc import ABC, abstractmethod


class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, num_results: int = 5) -> list[dict[str, str]]:
        """
        Search the internet/source.
        Returns a list of dicts with keys: 'title', 'url', 'snippet'.
        """

    @abstractmethod
    def fetch_content(self, url: str) -> str:
        """
        Fetch the full text content from a given URL.
        """
