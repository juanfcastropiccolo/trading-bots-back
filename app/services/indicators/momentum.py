import pandas as pd
from ta.momentum import RSIIndicator, StochRSIIndicator
from ta.trend import MACD

from app.services.indicators.base import BaseIndicator


class MomentumIndicator(BaseIndicator):
    name = "momentum"

    def calculate(self, df: pd.DataFrame) -> dict[str, float]:
        close = df["close"]

        # RSI
        rsi = RSIIndicator(close=close, window=14).rsi().iloc[-1]

        # Stochastic %K and %D
        stoch = StochRSIIndicator(close=close, window=14, smooth1=3, smooth2=3)
        stoch_k = stoch.stochrsi_k().iloc[-1] * 100
        stoch_d = stoch.stochrsi_d().iloc[-1] * 100

        # MACD
        macd = MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
        macd_line = macd.macd().iloc[-1]
        macd_signal = macd.macd_signal().iloc[-1]
        macd_hist = macd.macd_diff().iloc[-1]

        return {
            "rsi": round(float(rsi), 2),
            "stoch_k": round(float(stoch_k), 2),
            "stoch_d": round(float(stoch_d), 2),
            "macd_line": round(float(macd_line), 4),
            "macd_signal": round(float(macd_signal), 4),
            "macd_hist": round(float(macd_hist), 4),
        }
