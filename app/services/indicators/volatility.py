import pandas as pd
from ta.volatility import AverageTrueRange, BollingerBands

from app.services.indicators.base import BaseIndicator


class VolatilityIndicator(BaseIndicator):
    name = "volatility"

    def calculate(self, df: pd.DataFrame) -> dict[str, float]:
        close = df["close"]
        high = df["high"]
        low = df["low"]

        # ATR
        atr = AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range().iloc[-1]

        # Bollinger Bands
        bb = BollingerBands(close=close, window=20, window_dev=2)
        bb_upper = bb.bollinger_hband().iloc[-1]
        bb_middle = bb.bollinger_mavg().iloc[-1]
        bb_lower = bb.bollinger_lband().iloc[-1]
        bb_width = (bb_upper - bb_lower) / bb_middle if bb_middle else 0
        bb_pct = bb.bollinger_pband().iloc[-1]  # %B: position within bands

        # Parabolic SAR (manual calculation since ta lib's PSARIndicator needs enough data)
        psar = self._parabolic_sar(high, low, close)

        return {
            "atr": round(float(atr), 4),
            "bb_upper": round(float(bb_upper), 2),
            "bb_middle": round(float(bb_middle), 2),
            "bb_lower": round(float(bb_lower), 2),
            "bb_width": round(float(bb_width), 4),
            "bb_pct": round(float(bb_pct), 4),
            "psar": round(float(psar), 2),
        }

    def _parabolic_sar(self, high: pd.Series, low: pd.Series, close: pd.Series) -> float:
        """Simple Parabolic SAR calculation."""
        af_start = 0.02
        af_step = 0.02
        af_max = 0.20

        length = len(close)
        psar = close.iloc[0]
        bull = True
        af = af_start
        ep = high.iloc[0] if bull else low.iloc[0]

        for i in range(1, length):
            if bull:
                psar = psar + af * (ep - psar)
                psar = min(psar, low.iloc[i - 1])
                if i >= 2:
                    psar = min(psar, low.iloc[i - 2])
                if low.iloc[i] < psar:
                    bull = False
                    psar = ep
                    ep = low.iloc[i]
                    af = af_start
                else:
                    if high.iloc[i] > ep:
                        ep = high.iloc[i]
                        af = min(af + af_step, af_max)
            else:
                psar = psar + af * (ep - psar)
                psar = max(psar, high.iloc[i - 1])
                if i >= 2:
                    psar = max(psar, high.iloc[i - 2])
                if high.iloc[i] > psar:
                    bull = True
                    psar = ep
                    ep = high.iloc[i]
                    af = af_start
                else:
                    if low.iloc[i] < ep:
                        ep = low.iloc[i]
                        af = min(af + af_step, af_max)

        return psar
