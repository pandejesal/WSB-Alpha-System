from typing import Any, Literal

from pydantic import BaseModel, Field


class SleeveSignal(BaseModel):
    id: str
    signal: Literal["LONG", "FLAT", "SHORT", "HOLD"]
    confidence: float
    params: dict[str, Any] = Field(default_factory=dict)

class SignalsReport(BaseModel):
    run_id: str
    date: str
    mode: str
    sleeves: list[SleeveSignal]
