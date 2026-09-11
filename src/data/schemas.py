
import pandas as pd

try:
    import pandera as pa
    from pandera.typing import Series

    _PANDERA_AVAILABLE = True
except ModuleNotFoundError:
    pa = None  # type: ignore
    Series = None  # type: ignore
    _PANDERA_AVAILABLE = False


if _PANDERA_AVAILABLE:

    class OHLCVSchema(pa.DataFrameModel):  # type: ignore
        Ticker: Series[str] = pa.Field(coerce=True)  # type: ignore
        Date: Series[pd.Timestamp] = pa.Field(coerce=True)  # type: ignore
        Open: Series[float] = pa.Field(coerce=True, gt=0)  # type: ignore
        High: Series[float] = pa.Field(coerce=True, gt=0)  # type: ignore
        Low: Series[float] = pa.Field(coerce=True, gt=0)  # type: ignore
        Close: Series[float] = pa.Field(coerce=True, gt=0)  # type: ignore
        Volume: Series[int] = pa.Field(coerce=True, ge=0)  # type: ignore

        @pa.dataframe_check  # type: ignore
        def check_high_is_highest(cls, df: pd.DataFrame) -> Series[bool]:  # type: ignore
            return (df["High"] >= df["Low"]) & (df["High"] >= df["Open"]) & (df["High"] >= df["Close"])

        @pa.dataframe_check  # type: ignore
        def check_low_is_lowest(cls, df: pd.DataFrame) -> Series[bool]:  # type: ignore
            return (df["Low"] <= df["Open"]) & (df["Low"] <= df["Close"])

    class SentimentPostSchema(pa.DataFrameModel):  # type: ignore
        post_id: Series[str] = pa.Field(coerce=True)  # type: ignore
        post_date: Series[pd.Timestamp] = pa.Field(coerce=True)  # type: ignore
        ticker: Series[str] = pa.Field(coerce=True)  # type: ignore
        title: Series[str] = pa.Field(coerce=True)  # type: ignore
        sentiment_score: Series[float] = pa.Field(coerce=True, ge=-1.0, le=1.0)  # type: ignore
        content: Series[str] | None = pa.Field(coerce=True, nullable=True)  # type: ignore
        score: Series[float] | None = pa.Field(coerce=True, nullable=True)  # type: ignore

else:

    class _StubSchema:
        @classmethod
        def validate(cls, df: pd.DataFrame, *args, **kwargs) -> pd.DataFrame:
            # Minimal manual checks when pandera not installed: enforce High>=Low etc.
            if "High" in df.columns and "Low" in df.columns:
                if not (df["High"] >= df["Low"]).all():
                    raise ValueError("High must be >= Low")
                if "Open" in df.columns and not (df["High"] >= df["Open"]).all():
                    raise ValueError("High must be >= Open")
                if "Close" in df.columns and not (df["High"] >= df["Close"]).all():
                    raise ValueError("High must be >= Close")
            return df

    OHLCVSchema = _StubSchema  # type: ignore
    SentimentPostSchema = _StubSchema  # type: ignore
