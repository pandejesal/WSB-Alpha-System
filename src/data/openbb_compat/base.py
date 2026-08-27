"""
MIT License - Clean-room inspired by OpenBB-finance/OpenBB, not vendored
— AGPL text not copied.
"""

from typing import Any, Generic, TypeVar, Optional
from pydantic import BaseModel, field_validator
from datetime import date, datetime

class EmptyDataError(Exception):
    pass

class StandardQuery(BaseModel):
    symbol: str

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, v: str) -> str:
        return v.upper()

class StandardData(BaseModel):
    date: date

    @field_validator("date", mode="before")
    @classmethod
    def parse_date(cls, v: Any) -> date:
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v).date()
            except ValueError:
                pass
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, date):
            return v
        raise ValueError(f"Cannot parse date from {v}")

Q = TypeVar("Q", bound=StandardQuery)
R = TypeVar("R", bound=StandardData)

class AnnotatedResult(Generic[R]):
    def __init__(self, results: list[R], metadata: dict = None):
        self.results = results
        self.metadata = metadata or {}

class ProviderAdapter(Generic[Q, R]):
    def to_query(self, params: dict) -> Q:
        raise NotImplementedError

    def fetch(self, query: Q, creds: Optional[dict] = None) -> Any:
        raise NotImplementedError

    def to_records(self, query: Q, raw: Any) -> list[R] | AnnotatedResult[R]:
        raise NotImplementedError
