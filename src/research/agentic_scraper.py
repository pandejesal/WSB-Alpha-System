import logging
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

from src.research.browser_scraper import fetch_headlines as fallback_fetch_headlines

logger = logging.getLogger(__name__)

def fetch_agentic_headlines(ticker: str) -> list[dict[str, str]]:
    """
    Agentic Web Scraper using Playwright to extract financial headlines.
    Targets Yahoo Finance, extracting headline, URL, and source.
    Gracefully degrades to the basic browser scraper if Playwright fails.
    Never crashes.
    """
    results: list[dict[str, str]] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Use Yahoo finance news section
            search_url = f"https://finance.yahoo.com/quote/{ticker}/news/"

            # Simple timeout and wait strategy
            page.goto(search_url, timeout=15000, wait_until="domcontentloaded")

            # Extract
            # Looking for h3 elements which usually contain the news headlines on Yahoo Finance
            elements = page.query_selector_all("h3")

            for elem in elements:
                # Yahoo Finance has various h3 tags, we just filter out short/irrelevant ones
                headline_text = elem.inner_text().strip()
                if headline_text and len(headline_text) > 20 and "Trending Tickers" not in headline_text and "U.S. markets" not in headline_text:
                    # Find a link if it exists inside the h3, or a parent
                    link_elem = elem.query_selector("a")
                    url_text = link_elem.get_attribute("href") if link_elem else ""
                    if url_text and not url_text.startswith("http"):
                        url_text = f"https://finance.yahoo.com{url_text}"

                    results.append({
                        "headline": headline_text,
                        "source": "Yahoo Finance (Agentic)",
                        "url": url_text,
                        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                    })

                if len(results) >= 10:
                    break

            if len(results) < 10:
                logger.info(f"Trying duckduckgo for {ticker}")

                # Use DuckDuckGo HTML search for a lightweight, JS-free search
                search_url = f"https://html.duckduckgo.com/html/?q={ticker}+stock+news"

                # Simple timeout and wait strategy
                page.goto(search_url, timeout=15000, wait_until="domcontentloaded")

                # Wait for results
                page.wait_for_selector(".result", timeout=10000)

                # Extract
                elements = page.query_selector_all(".result")
                for elem in elements[:10]: # Limit to top 10 results
                    headline_elem = elem.query_selector(".result__title")
                    snippet_elem = elem.query_selector(".result__snippet")
                    url_elem = elem.query_selector(".result__url")

                    if headline_elem:
                        headline_text = headline_elem.inner_text().strip()
                        url_text = url_elem.get_attribute("href") if url_elem else ""
                        # Duckduckgo HTML might not have a clean source name, use snippet or URL base
                        source_name = url_elem.inner_text().strip() if url_elem else "DuckDuckGo"

                        if headline_text and not any(h["headline"] == headline_text for h in results):
                            results.append({
                                "headline": headline_text,
                                "source": source_name,
                                "url": url_text,
                                "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                            })

                        if len(results) >= 10:
                            break

            browser.close()

            if results:
                logger.info(f"Successfully fetched {len(results)} agentic headlines for {ticker}.")
                return results
            else:
                logger.warning(f"Agentic scraper found no results for {ticker}, falling back.")

    except Exception as e:
        logger.warning(f"Agentic scraper failed for {ticker}: {e}. Falling back.")

    # Fallback Mechanism
    try:
        fallback_headlines = fallback_fetch_headlines(ticker)
        for h in fallback_headlines:
            results.append({
                "headline": h,
                "source": "Fallback Yahoo RSS",
                "url": "",
                "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            })
        logger.info(f"Fallback successfully loaded {len(results)} headlines for {ticker}.")
    except Exception as e:
        logger.error(f"Fallback scraper totally failed for {ticker}: {e}. Returning empty list.")

    return results
