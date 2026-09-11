"""Scrapling-backed document fetcher for the research queue (B5b ADOPT ticket).

Conforms to ``src.research.base_search.SearchProvider`` (search + fetch_content).
Plain-tier fetcher only (no Playwright/stealth — browser overhead breaks CI).

- File cache first: ``docs/data/scrape_cache/<sha256(url)>.md``. No network
  when cached. Never called from the hot evolve loop — research queue only.
- ``scrapling`` is an OPTIONAL dependency (``pip install scrapling`` to enable).
  Missing library -> informative ImportError (arch-pattern fail-closed).
- Any fetch/parse failure -> RuntimeError with URL + cause (fail-closed loudly,
  never silent empty content that poisons downstream debate).
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from src.research.base_search import SearchProvider

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "data" / "scrape_cache"


def _extract_text(page: object) -> str:
    """Best-effort text out of a scrapling page object across API shapes."""
    for attr in ("text", "body", "content", "markdown"):
        try:
            val = getattr(page, attr, None)
            text = val() if callable(val) else val
            if isinstance(text, str) and text.strip():
                return text.strip()
        except Exception as exc:  # noqa: BLE001 - unknown third-party page shapes
            logger.debug("scrapling page shape %r unreadable: %s", attr, exc)
            continue
    title = getattr(page, "title", "")
    if isinstance(title, str) and title.strip():
        return title.strip()
    raise RuntimeError("unrecognized scrapling page shape (no text/body/content)")


class ScraplingProvider(SearchProvider):
    """Document fetcher via Scrapling plain-tier HTTP (cached, research only)."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir else CACHE_DIR

    def search(self, query: str, num_results: int = 5) -> list[dict[str, str]]:
        """Scrapling is a fetcher, not a search engine: fail loudly, not empty."""
        raise NotImplementedError(
            "ScraplingProvider has no search index; use GoogleSearchProvider for "
            f"search, then fetch_content() here. Query was: {query!r} (limit {num_results})"
        )

    def fetch_content(self, url: str) -> str:
        """Fetch URL text via cache-first Scrapling plain tier."""
        if not url or not url.startswith(("http://", "https://")):
            raise ValueError(f"refusing non-http(s) url: {url!r}")
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        cached = self.cache_dir / f"{digest}.md"
        if cached.exists():
            return cached.read_text(encoding="utf-8")
        try:
            import scrapling
        except ModuleNotFoundError as exc:
            raise ImportError(
                "scrapling not installed — run `pip install scrapling` to enable "
                "ScraplingProvider (plain tier only; no Playwright needed)"
            ) from exc
        fetcher_cls = getattr(scrapling, "Fetcher", None)
        if fetcher_cls is None:
            raise RuntimeError("scrapling has no Fetcher class in this version")
        try:
            page = fetcher_cls().get(url)
            text = _extract_text(page)
        except Exception as exc:
            raise RuntimeError(f"scrapling fetch failed for {url}: {exc}") from exc
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cached.write_text(text, encoding="utf-8")
        except OSError as exc:
            logger.warning("scrape cache write failed for %s: %s", url, exc)
        return text
