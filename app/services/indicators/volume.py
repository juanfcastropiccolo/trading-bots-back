import pandas as pd
from ta.volume import OnBalanceVolumeIndicator

from app.services.indicators.base import BaseIndicator


class VolumeIndicator(BaseIndicator):
    name = "volume"

    def calculate(self, df: pd.DataFrame) -> dict[str, float]:
        close = df["close"]
        volume = df["volume"]

        # OBV
        obv_series = OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()
        obv = obv_series.iloc[-1]
        obv_prev = obv_series.iloc[-2] if len(obv_series) >= 2 else obv

        # Volume SMA(20)
        window = min(20, len(volume))
        vol_sma = volume.rolling(window=window).mean().iloc[-1]
        vol_current = volume.iloc[-1]
        vol_ratio = vol_current / vol_sma if vol_sma > 0 else 1.0

        return {
            "obv": round(float(obv), 2),
            "obv_delta": round(float(obv - obv_prev), 2),
            "vol_sma_20": round(float(vol_sma), 2),
            "vol_ratio": round(float(vol_ratio), 4),
        }
