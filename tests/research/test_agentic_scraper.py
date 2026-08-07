import unittest
from unittest.mock import patch, MagicMock

from src.research.agentic_scraper import fetch_agentic_headlines


class TestAgenticScraper(unittest.TestCase):
    @patch("src.research.agentic_scraper.sync_playwright")
    def test_fetch_agentic_headlines_success(self, mock_playwright):
        # Setup mock playwright
        mock_p = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()

        mock_playwright.return_value.__enter__.return_value = mock_p
        mock_p.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        # Setup mock elements
        mock_elem1 = MagicMock()
        mock_elem1.inner_text.return_value = "Breaking News 1 is more than 20 chars"
        mock_link1 = MagicMock()
        mock_link1.get_attribute.return_value = "/news/1"
        mock_elem1.query_selector.return_value = mock_link1

        mock_elem2 = MagicMock()
        mock_elem2.inner_text.return_value = "Breaking News 2 is also long enough"
        mock_link2 = MagicMock()
        mock_link2.get_attribute.return_value = "https://example.com/news/2"
        mock_elem2.query_selector.return_value = mock_link2

        # We need to distinct them so they don't get appended again on fallback
        mock_page.query_selector_all.side_effect = [
            [mock_elem1, mock_elem2], # for yahoo
            [] # for duckduckgo
        ]

        results = fetch_agentic_headlines("AAPL")

        self.assertEqual(len(results), 2)

        self.assertEqual(results[0]["headline"], "Breaking News 1 is more than 20 chars")
        self.assertEqual(results[0]["source"], "Yahoo Finance (Agentic)")
        self.assertEqual(results[0]["url"], "https://finance.yahoo.com/news/1")

        self.assertEqual(results[1]["headline"], "Breaking News 2 is also long enough")
        self.assertEqual(results[1]["source"], "Yahoo Finance (Agentic)")
        self.assertEqual(results[1]["url"], "https://example.com/news/2")

    @patch("src.research.agentic_scraper.sync_playwright")
    @patch("src.research.agentic_scraper.fallback_fetch_headlines")
    def test_fetch_agentic_headlines_fallback(self, mock_fallback, mock_playwright):
        # Force Playwright exception
        mock_playwright.side_effect = Exception("Playwright crash")
        mock_fallback.return_value = ["Fallback Headline 1"]

        results = fetch_agentic_headlines("AAPL")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["headline"], "Fallback Headline 1")
        self.assertEqual(results[0]["source"], "Fallback Yahoo RSS")

    @patch("src.research.agentic_scraper.sync_playwright")
    @patch("src.research.agentic_scraper.fallback_fetch_headlines")
    def test_fetch_agentic_headlines_total_failure(self, mock_fallback, mock_playwright):
        # Force Playwright exception
        mock_playwright.side_effect = Exception("Playwright crash")
        # Force Fallback exception
        mock_fallback.side_effect = Exception("Fallback crash")

        # Should not raise exception
        results = fetch_agentic_headlines("AAPL")

        self.assertEqual(results, [])
