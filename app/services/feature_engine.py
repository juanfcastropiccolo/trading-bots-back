import logging
import pandas as pd
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange

from app.services.indicators import INDICATOR_REGISTRY

logger = logging.getLogger(__name__)


def calculate_features(df: pd.DataFrame) -> dict | None:
    """Calculate basic features (backward-compatible)."""
    if len(df) < 30:
        return None

    close = df["close"]
    high = df["high"]
    low = df["low"]

    ema_fast = EMAIndicator(close=close, window=9).ema_indicator().iloc[-1]
    ema_slow = EMAIndicator(close=close, window=21).ema_indicator().iloc[-1]
    rsi = RSIIndicator(close=close, window=14).rsi().iloc[-1]
    atr = AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range().iloc[-1]

    return {
        "ema_fast": float(round(ema_fast, 2)),
        "ema_slow": float(round(ema_slow, 2)),
        "rsi": float(round(rsi, 2)),
        "atr": float(round(atr, 2)),
        "close": float(round(close.iloc[-1], 2)),
    }


def calculate_features_extended(df: pd.DataFrame) -> dict | None:
    """Calculate all indicators from the registry (~25 features).

    Returns None if not enough data. Includes backward-compatible keys
    (ema_fast, ema_slow, rsi, atr, close) plus all extended indicators.
    """
    if len(df) < 30:
        return None

    features = {}
    for indicator in INDICATOR_REGISTRY:
        try:
            result = indicator.calculate(df)
            features.update(result)
        except Exception as e:
            logger.warning(f"Indicator {indicator.name} failed: {e}")

    # Backward-compatible aliases
    features["ema_fast"] = features.get("ema_9", 0.0)
    features["ema_slow"] = features.get("ema_21", 0.0)
    features["close"] = float(round(df["close"].iloc[-1], 2))

    return features
