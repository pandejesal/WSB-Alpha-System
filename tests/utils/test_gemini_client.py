import pytest
from unittest.mock import patch, MagicMock
from src.utils.gemini_client import RateLimitedGeminiClient, RateLimiter, TokenBucketLimiter

def test_token_bucket_wait():
    # Capacity 2, 2 tokens/sec
    limiter = TokenBucketLimiter(capacity=2, fill_rate=2.0)
    # Start full. Consume 2 tokens.
    limiter.wait_if_needed(2)
    assert limiter.tokens < 1.0

def test_generate_content_flash_fallback_to_lite():
    client = RateLimitedGeminiClient(api_key="mock_key")

    with patch.object(client, '_generate_lite', return_value="Lite Fallback") as mock_lite:
        with patch.object(client.client.models, 'generate_content', side_effect=Exception("429 Quota Exhausted")) as mock_flash:
            with patch('time.sleep'):
                res = client.generate_content("Hello")

    mock_flash.assert_called_once()
    mock_lite.assert_called_once()
    assert res == "Lite Fallback"

def test_generate_content_lite_fallback_to_local():
    client = RateLimitedGeminiClient(api_key="mock_key")

    with patch.object(client.client.models, 'generate_content', side_effect=Exception("429 Quota Exhausted")):
        with patch.object(client, '_generate_lite', side_effect=Exception("Lite failed too")):
            with patch.object(client, '_fallback_local_llm', return_value="Local Fallback") as mock_local:
                with patch('time.sleep'):
                    res = client.generate_content("Hello")

    mock_local.assert_called_once()
    assert res == "Local Fallback"

def test_generate_content_no_key_local():
    client = RateLimitedGeminiClient(api_key="")

    with patch.object(client, '_fallback_local_llm', return_value="No key local") as mock_local:
        res = client.generate_content("Hello")

    mock_local.assert_called_once()
    assert res == "No key local"

def test_fallback_local_llm_graceful_fail():
    client = RateLimitedGeminiClient(api_key="")
    with patch('requests.post', side_effect=Exception("Network error")):
        res = client._fallback_local_llm("Test")
    assert res is None
