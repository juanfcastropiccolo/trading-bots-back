import pandas as pd
from ta.trend import EMAIndicator

from app.services.indicators.base import BaseIndicator


class MovingAveragesIndicator(BaseIndicator):
    name = "moving_averages"

    def calculate(self, df: pd.DataFrame) -> dict[str, float]:
        close = df["close"]
        ema9 = EMAIndicator(close=close, window=9).ema_indicator().iloc[-1]
        ema21 = EMAIndicator(close=close, window=21).ema_indicator().iloc[-1]
        ema50 = EMAIndicator(close=close, window=min(50, len(close))).ema_indicator().iloc[-1]

        return {
            "ema_9": round(float(ema9), 2),
            "ema_21": round(float(ema21), 2),
            "ema_50": round(float(ema50), 2),
        }
