from app.services.strategies.base import BaseStrategy, StrategyVote


class MACDStrategy(BaseStrategy):
    name = "macd"
    default_weight = 1.2

    def evaluate(self, features: dict, prev_features: dict | None = None, params: dict | None = None) -> StrategyVote:
        macd_line = features.get("macd_line", 0)
        macd_signal = features.get("macd_signal", 0)
        macd_hist = features.get("macd_hist", 0)

        score = 0.0
        reasons = []

        # Signal line crossover
        if prev_features:
            prev_hist = prev_features.get("macd_hist", 0)
            if prev_hist <= 0 < macd_hist:
                score += 0.6
                reasons.append("MACD bullish crossover")
            elif prev_hist >= 0 > macd_hist:
                score -= 0.6
                reasons.append("MACD bearish crossover")

        # Histogram momentum
        if macd_hist > 0:
            score += 0.2
            reasons.append("positive histogram")
        elif macd_hist < 0:
            score -= 0.2
            reasons.append("negative histogram")

        # Zero-line cross
        if prev_features:
            prev_macd = prev_features.get("macd_line", 0)
            if prev_macd <= 0 < macd_line:
                score += 0.3
                reasons.append("MACD crossed above zero")
            elif prev_macd >= 0 > macd_line:
                score -= 0.3
                reasons.append("MACD crossed below zero")

        score = max(-1.0, min(1.0, score))
        return StrategyVote(
            name=self.name,
            score=round(score, 3),
            reason="; ".join(reasons) if reasons else "no signal",
        )
