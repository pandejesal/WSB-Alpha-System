import pandas as pd
import pandera as pa
from pandera.typing import Series
from typing import Optional

class OHLCVSchema(pa.DataFrameModel):
    Ticker: Series[str] = pa.Field(coerce=True)
    Date: Series[pd.Timestamp] = pa.Field(coerce=True)
    Open: Series[float] = pa.Field(coerce=True, gt=0)
    High: Series[float] = pa.Field(coerce=True, gt=0)
    Low: Series[float] = pa.Field(coerce=True, gt=0)
    Close: Series[float] = pa.Field(coerce=True, gt=0)
    Volume: Series[int] = pa.Field(coerce=True, ge=0)

    @pa.dataframe_check
    def check_high_is_highest(cls, df: pd.DataFrame) -> Series[bool]:
        # High must be >= Low, Open, Close
        return (df["High"] >= df["Low"]) & (df["High"] >= df["Open"]) & (df["High"] >= df["Close"])

    @pa.dataframe_check
    def check_low_is_lowest(cls, df: pd.DataFrame) -> Series[bool]:
        # Low must be <= Open, Close
        return (df["Low"] <= df["Open"]) & (df["Low"] <= df["Close"])

class SentimentPostSchema(pa.DataFrameModel):
    post_id: Series[str] = pa.Field(coerce=True)
    post_date: Series[pd.Timestamp] = pa.Field(coerce=True)
    ticker: Series[str] = pa.Field(coerce=True)
    title: Series[str] = pa.Field(coerce=True)
    sentiment_score: Series[float] = pa.Field(coerce=True, ge=-1.0, le=1.0)
    content: Optional[Series[str]] = pa.Field(coerce=True, nullable=True)
    score: Optional[Series[float]] = pa.Field(coerce=True, nullable=True)
