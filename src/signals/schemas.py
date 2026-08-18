from pydantic import BaseModel, Field
from typing import Dict, Any, List, Literal

class SleeveSignal(BaseModel):
    id: str
    signal: Literal["LONG", "FLAT", "SHORT", "HOLD"]
    confidence: float
    params: Dict[str, Any] = Field(default_factory=dict)

class SignalsReport(BaseModel):
    run_id: str
    date: str
    mode: str
    sleeves: List[SleeveSignal]
