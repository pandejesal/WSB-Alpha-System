from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class LLMProvider(ABC):
    @abstractmethod
    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text from the LLM based on a prompt."""
        pass

    @abstractmethod
    def generate_json(self, prompt: str, schema: Any, **kwargs) -> Dict:
        """Generate structured JSON conforming to a schema."""
        pass
