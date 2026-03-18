import pandas as pd
from ta.trend import ADXIndicator

from app.services.indicators.base import BaseIndicator


class TrendIndicator(BaseIndicator):
    name = "trend"

    def calculate(self, df: pd.DataFrame) -> dict[str, float]:
        close = df["close"]
        high = df["high"]
        low = df["low"]

        # ADX with +DI/-DI
        adx_ind = ADXIndicator(high=high, low=low, close=close, window=14)
        adx = adx_ind.adx().iloc[-1]
        plus_di = adx_ind.adx_pos().iloc[-1]
        minus_di = adx_ind.adx_neg().iloc[-1]

        # Donchian Channel (20-period)
        window = min(20, len(high))
        donchian_high = high.rolling(window=window).max().iloc[-1]
        donchian_low = low.rolling(window=window).min().iloc[-1]
        donchian_mid = (donchian_high + donchian_low) / 2

        return {
            "adx": round(float(adx), 2),
            "plus_di": round(float(plus_di), 2),
            "minus_di": round(float(minus_di), 2),
            "donchian_high": round(float(donchian_high), 2),
            "donchian_low": round(float(donchian_low), 2),
            "donchian_mid": round(float(donchian_mid), 2),
        }
