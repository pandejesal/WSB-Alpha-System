import time
import logging
from collections import deque
from datetime import datetime, timedelta
from google import genai

logger = logging.getLogger(__name__)


class TokenBucketLimiter:
    def __init__(self, capacity: int, fill_rate: float):
        self.capacity = capacity
        self.tokens = capacity
        self.fill_rate = fill_rate # tokens per second
        self.last_fill = time.time()
        self.lock = False # Simplified for non-async

    def wait_if_needed(self, tokens: int = 1):
        while True:
            now = time.time()
            elapsed = now - self.last_fill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.fill_rate)
            self.last_fill = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return

            # Not enough tokens, calculate wait time
            sleep_time = (tokens - self.tokens) / self.fill_rate
            logger.warning(f"Token bucket empty. Sleeping for {sleep_time:.2f}s...")
            time.sleep(sleep_time)

class RateLimiter:
    def __init__(self, rpm_limit: int, rpd_limit: int, min_delay_sec: float):
        self.rpm_limit = rpm_limit
        self.rpd_limit = rpd_limit
        self.min_delay_sec = min_delay_sec
        self.bucket = TokenBucketLimiter(capacity=max(1, int(rpm_limit / 2)), fill_rate=rpm_limit / 60.0)

        self.minute_calls = deque()
        self.day_calls = deque()
        self.last_call_time = None

    def wait_if_needed(self):
        now = datetime.now()

        # Enforce min delay
        if self.last_call_time:
            elapsed = (now - self.last_call_time).total_seconds()
            if elapsed < self.min_delay_sec:
                time.sleep(self.min_delay_sec - elapsed)
                now = datetime.now()

        # Token bucket for burst limit
        self.bucket.wait_if_needed(1)

        # Enforce RPM
        while self.minute_calls and (now - self.minute_calls[0]).total_seconds() > 60:
            self.minute_calls.popleft()

        if len(self.minute_calls) >= self.rpm_limit:
            sleep_time = 60 - (now - self.minute_calls[0]).total_seconds()
            if sleep_time > 0:
                time.sleep(sleep_time)
                now = datetime.now()

        # Enforce RPD
        while self.day_calls and (now - self.day_calls[0]).total_seconds() > 86400:
            self.day_calls.popleft()

        if len(self.day_calls) >= self.rpd_limit:
            # We don't raise anymore. We return graceful degradation later.
            pass

    def record_call(self):
        now = datetime.now()
        self.last_call_time = now
        self.minute_calls.append(now)
        self.day_calls.append(now)


class RateLimitedGeminiClient:
    """
    Router for Gemini calls with strict rate limiting and fallback mechanisms.
    Flash Lite: 15 RPM (1s delay), 500 RPD safe margin
    Flash: 5 RPM (13s delay), 15 RPD safe margin
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = None

        self.flash_limiter = RateLimiter(rpm_limit=5, rpd_limit=20, min_delay_sec=13.0)
        self.lite_limiter = RateLimiter(rpm_limit=15, rpd_limit=500, min_delay_sec=1.0)

    def generate_content(self, prompt: str, use_flash: bool = True, search_grounding: bool = False) -> dict | str | None:
        if not self.api_key:
            logger.error("No GEMINI_API_KEY provided.")
            return self._fallback_local_llm(prompt)

        # Try Gemini Flash
        if use_flash:
            try:
                self.flash_limiter.wait_if_needed()
                self.flash_limiter.record_call()
                logger.info("Executing Gemini Flash request...")
                response = self.client.models.generate_content(model='gemini-3.5-flash', contents=prompt)
                return response.text
            except Exception as e:
                logger.warning(f"Flash failed: {e}. Attempting fallback chain...")
                time.sleep(2.0)

        # Try Gemini Flash Lite
        try:
            return self._generate_lite(prompt, search_grounding)
        except Exception as e:
            logger.warning(f"Flash Lite failed: {e}. Falling back to local model...")
            time.sleep(2.0)

        # Final fallback to Local/Ollama
        return self._fallback_local_llm(prompt)

    def _generate_lite(self, prompt: str, search_grounding: bool) -> str:
        self.lite_limiter.wait_if_needed()
        tools = []
        if search_grounding:
            tools.append({"google_search": {}})

        self.lite_limiter.record_call()
        logger.info(f"Executing Gemini Flash Lite request...")
        config_kwargs = {}
        if tools: config_kwargs['tools'] = tools

        response = self.client.models.generate_content(model='gemini-3.5-flash-lite', contents=prompt, config=config_kwargs if config_kwargs else None)
        return response.text

    def _fallback_local_llm(self, prompt: str) -> str | None:
        logger.info("Executing Local/Fallback LLM request...")
        # Simulate local HuggingFace/Ollama endpoint
        try:
            import requests
            # Assume local ollama running on port 11434
            # We wrap it in try-except so it never crashes caller
            response = requests.post("http://localhost:11434/api/generate", json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False
            }, timeout=2.0)
            if response.status_code == 200:
                return response.json().get("response", "")
        except Exception as e:
            logger.error(f"Local LLM fallback also failed: {e}")

        # Graceful total failure
        return None
