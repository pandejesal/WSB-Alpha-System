"""Tests for ScraplingProvider (B5b ticket). No network, no scrapling install needed."""

import pytest

from src.research.scrapling_provider import ScraplingProvider, _extract_text


def test_rejects_non_http():
    p = ScraplingProvider()
    with pytest.raises(ValueError):
        p.fetch_content("ftp://example.com/x")
    with pytest.raises(ValueError):
        p.fetch_content("")


def test_search_is_loud_not_implemented():
    p = ScraplingProvider()
    with pytest.raises(NotImplementedError):
        p.search("earnings calls")


def test_cache_hit_no_network(tmp_path):
    p = ScraplingProvider(cache_dir=tmp_path)
    url = "https://example.com/earnings"
    import hashlib

    (tmp_path / f"{hashlib.sha256(url.encode()).hexdigest()[:16]}.md").write_text(
        "cached earnings text", encoding="utf-8"
    )
    assert p.fetch_content(url) == "cached earnings text"


def test_missing_lib_fail_closed(tmp_path):
    p = ScraplingProvider(cache_dir=tmp_path)
    with pytest.raises(ImportError, match="pip install scrapling"):
        p.fetch_content("https://example.com/unseen")


def test_extract_text_shapes():
    class P1:
        text = "hello"

    class P2:
        title = "only title"

    class P3:
        pass

    assert _extract_text(P1()) == "hello"
    assert _extract_text(P2()) == "only title"
    with pytest.raises(RuntimeError):
        _extract_text(P3())
