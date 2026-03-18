import numpy as np


class FeatureDiscretizer:
    """Discretize continuous features into bins for Q-table indexing.

    State space: RSI(5) × MACD_hist(3) × ADX(3) × BB_position(3) × EMA_align(2) = 270 states
    """

    # Bin definitions
    RSI_BINS = [0, 20, 40, 60, 80, 100]  # 5 bins
    MACD_BINS = [-np.inf, -0.001, 0.001, np.inf]  # 3 bins: negative, neutral, positive
    ADX_BINS = [0, 20, 40, np.inf]  # 3 bins: weak, moderate, strong
    BB_BINS = [0, 0.3, 0.7, 1.0]  # 3 bins: lower, middle, upper
    EMA_ALIGN = 2  # 0=bearish, 1=bullish

    N_STATES = 5 * 3 * 3 * 3 * 2  # 270
    N_ACTIONS = 3  # 0=HOLD, 1=BUY, 2=SELL

    def discretize(self, features: dict) -> int:
        """Convert continuous features to a single state index."""
        rsi_bin = self._bin(features.get("rsi", 50), self.RSI_BINS)
        macd_bin = self._bin(features.get("macd_hist", 0), self.MACD_BINS)
        adx_bin = self._bin(features.get("adx", 0), self.ADX_BINS)
        bb_bin = self._bin(features.get("bb_pct", 0.5), self.BB_BINS)

        ema_fast = features.get("ema_fast", features.get("ema_9", 0))
        ema_slow = features.get("ema_slow", features.get("ema_21", 0))
        ema_align = 1 if ema_fast > ema_slow else 0

        # Multi-dimensional index → flat index
        state = (
            rsi_bin * (3 * 3 * 3 * 2)
            + macd_bin * (3 * 3 * 2)
            + adx_bin * (3 * 2)
            + bb_bin * 2
            + ema_align
        )
        return min(state, self.N_STATES - 1)

    def _bin(self, value: float, edges: list) -> int:
        """Assign value to bin based on edges."""
        for i in range(len(edges) - 1):
            if value <= edges[i + 1]:
                return i
        return len(edges) - 2
