"""
MIT License - Clean-room inspired by OpenBB-finance/OpenBB, not vendored
— AGPL text not copied.
"""

from typing import Dict
from .base import ProviderAdapter
from importlib.metadata import entry_points

class Registry:
    def __init__(self):
        self.providers: Dict[str, ProviderAdapter] = {}

    def include(self, name: str, adapter: ProviderAdapter) -> None:
        self.providers[name] = adapter

    def get(self, name: str) -> ProviderAdapter:
        if name not in self.providers:
            raise KeyError(f"Provider '{name}' not found in registry.")
        return self.providers[name]

    @classmethod
    def default(cls) -> "Registry":
        return cls()

class RegistryLoader:
    @staticmethod
    def from_entrypoints() -> Registry:
        registry = Registry()
        try:
            # For Python 3.10+ importlib.metadata
            eps = entry_points(group="wsb.providers")
            for ep in eps:
                adapter_cls = ep.load()
                registry.include(ep.name, adapter_cls())
        except Exception:
            # For older Python or if group doesn't exist
            pass
        return registry
