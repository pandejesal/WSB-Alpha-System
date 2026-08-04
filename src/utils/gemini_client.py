import time
import logging
from collections import deque
from datetime import datetime, timedelta
from google import genai

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, rpm_limit: int, rpd_limit: int, min_delay_sec: float):
        self.rpm_limit = rpm_limit
        self.rpd_limit = rpd_limit
        self.min_delay_sec = min_delay_sec

        self.minute_calls = deque()
        self.day_calls = deque()
        self.last_call_time = None

    def wait_if_needed(self):
        now = datetime.now()

        # 1. Enforce min delay between calls
        if self.last_call_time:
            elapsed = (now - self.last_call_time).total_seconds()
            if elapsed < self.min_delay_sec:
                sleep_time = self.min_delay_sec - elapsed
                logger.debug(f"Pacing limit hit. Sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)
                now = datetime.now()

        # 2. Enforce RPM (Requests Per Minute)
        while self.minute_calls and (now - self.minute_calls[0]).total_seconds() > 60:
            self.minute_calls.popleft()

        if len(self.minute_calls) >= self.rpm_limit:
            sleep_time = 60 - (now - self.minute_calls[0]).total_seconds()
            if sleep_time > 0:
                logger.warning(f"RPM limit hit. Sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)
                now = datetime.now()

        # 3. Enforce RPD (Requests Per Day)
        while self.day_calls and (now - self.day_calls[0]).total_seconds() > 86400:
            self.day_calls.popleft()

        if len(self.day_calls) >= self.rpd_limit:
            logger.critical("DAILY QUOTA EXHAUSTED! Halting execution.")
            raise Exception("429 Quota Exhausted: Daily limit reached.")

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

    def generate_content(self, prompt: str, use_flash: bool = True, search_grounding: bool = False) -> str:
        if not self.api_key:
            logger.error("No GEMINI_API_KEY provided.")
            return ""

        if use_flash:
            try:
                self.flash_limiter.wait_if_needed()
                self.flash_limiter.record_call()
                logger.info("Executing Gemini Flash request...")
                response = self.client.models.generate_content(model='gemini-3.5-flash', contents=prompt)
                return response.text
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "Quota Exhausted" in error_str:
                    logger.warning("Flash 429 Quota Exhausted. Falling back to Flash Lite with 5s sleep...")
                    time.sleep(5.0)
                    return self._generate_lite(prompt, search_grounding)
                else:
                    logger.error(f"Flash request failed: {e}")
                    raise e
        else:
            return self._generate_lite(prompt, search_grounding)

    def _generate_lite(self, prompt: str, search_grounding: bool) -> str:
        self.lite_limiter.wait_if_needed()

        tools = []
        if search_grounding:
            # Using google-genai search grounding tool
            tools.append({"google_search": {}})

        self.lite_limiter.record_call()
        logger.info(f"Executing Gemini Flash Lite request... (Search Grounding: {search_grounding})")

        # New SDK grounding syntax conceptually (passing tools list to config)
        config_kwargs = {}
        if tools: config_kwargs['tools'] = tools

        response = self.client.models.generate_content(model='gemini-3.5-flash-lite', contents=prompt, config=config_kwargs if config_kwargs else None)
        return response.text
