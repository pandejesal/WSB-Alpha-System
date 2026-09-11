"""Scrapling-backed document fetcher for the research queue (B5b ADOPT ticket).

Conforms to ``src.research.base_search.SearchProvider`` (search + fetch_content).
Plain-tier fetcher only (no Playwright/stealth — browser overhead breaks CI).

- File cache first: ``docs/data/scrape_cache/<sha256(url)>.md``. No network
  when cached. Never called from the hot evolve loop — research queue only.
- Plain HTTP via stdlib ``urllib`` + ``scrapling.parser.Adaptor`` for parsing
  (no Playwright/browser needed — the ``Fetcher`` chain hard-requires it).
  ``scrapling`` is still an optional dep: missing library -> informative
  ImportError (arch-pattern fail-closed).
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
    for attr in ("get_all_text", "text", "body", "content", "markdown"):
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
        """Fetch URL text via cache-first plain HTTP + scrapling Adaptor parse."""
        if not url or not url.startswith(("http://", "https://")):
            raise ValueError(f"refusing non-http(s) url: {url!r}")
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        cached = self.cache_dir / f"{digest}.md"
        if cached.exists():
            return cached.read_text(encoding="utf-8")
        try:
            from scrapling.parser import Adaptor  # optional dep, lazy import
        except ImportError as exc:
            raise ImportError(
                "scrapling not installed — run `pip install scrapling` to enable "
                "ScraplingProvider (plain tier only; no Playwright needed)"
            ) from exc
        try:
            import urllib.request

            req = urllib.request.Request(
                url, headers={"User-Agent": "WSB-Alpha-Research/1.0 (paper research)"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read()
            text = _extract_text(Adaptor(html, url=url))
            if not text:
                raise RuntimeError("empty parse result")
        except Exception as exc:
            raise RuntimeError(f"scrapling fetch failed for {url}: {exc}") from exc
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cached.write_text(text, encoding="utf-8")
        except OSError as exc:
            logger.warning("scrape cache write failed for %s: %s", url, exc)
        return text
