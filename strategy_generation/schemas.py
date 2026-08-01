from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal

class Parameter(BaseModel):
    name: str
    type: Literal["int", "float", "bool", "str"]
    default: float | int | str | bool
    min_value: Optional[float] = None
    max_value: Optional[float] = None

class SignalCondition(BaseModel):
    indicator: str
    operator: Literal[">", "<", ">=", "<=", "==", "!=", "crossover", "crossunder"]
    value: str | float # Can be another indicator name or a static value

class StrategySpecification(BaseModel):
    id: str = Field(..., description="Unique UUID for the strategy")
    name: str = Field(..., description="Human readable name")
    description: str = Field(..., description="Hypothesis and logic description")
    asset_classes: List[str] = Field(default_factory=list, description="Preferred asset classes (e.g. crypto, equities)")
    timeframes: List[str] = Field(default_factory=list, description="Supported timeframes (e.g. 1d, 1h)")
    parameters: List[Parameter] = Field(default_factory=list, description="Tunable parameters for optimization")

    # These represent the core logic extracted from the research
    entry_conditions_long: List[SignalCondition] = Field(default_factory=list)
    entry_conditions_short: List[SignalCondition] = Field(default_factory=list)
    exit_conditions_long: List[SignalCondition] = Field(default_factory=list)
    exit_conditions_short: List[SignalCondition] = Field(default_factory=list)

    # Risk and Regime
    stop_loss_pct: Optional[float] = Field(None, description="Static stop loss percentage")
    take_profit_pct: Optional[float] = Field(None, description="Static take profit percentage")
    preferred_regimes: List[str] = Field(default_factory=list, description="e.g. bull, high_volatility")
