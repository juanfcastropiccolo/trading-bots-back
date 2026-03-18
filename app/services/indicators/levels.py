import pandas as pd

from app.services.indicators.base import BaseIndicator


class FibonacciIndicator(BaseIndicator):
    name = "fibonacci"

    def calculate(self, df: pd.DataFrame) -> dict[str, float]:
        high = df["high"]
        low = df["low"]
        close = df["close"]

        # Use the range of the available data for Fibonacci levels
        swing_high = float(high.max())
        swing_low = float(low.min())
        diff = swing_high - swing_low
        current_close = float(close.iloc[-1])

        fib_382 = swing_high - diff * 0.382
        fib_500 = swing_high - diff * 0.500
        fib_618 = swing_high - diff * 0.618

        # Distance from current price to nearest Fib level (normalized by ATR-like range)
        fib_levels = [fib_382, fib_500, fib_618]
        nearest_dist = min(abs(current_close - level) for level in fib_levels)
        fib_proximity = nearest_dist / diff if diff > 0 else 1.0

        return {
            "fib_382": round(fib_382, 2),
            "fib_500": round(fib_500, 2),
            "fib_618": round(fib_618, 2),
            "fib_proximity": round(float(fib_proximity), 4),
        }
