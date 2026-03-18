from app.services.strategies.base import BaseStrategy, StrategyVote


class ParabolicSARStrategy(BaseStrategy):
    name = "parabolic_sar"
    default_weight = 0.8

    def evaluate(self, features: dict, prev_features: dict | None = None, params: dict | None = None) -> StrategyVote:
        close = features.get("close", 0)
        psar = features.get("psar", 0)

        if not close or not psar:
            return StrategyVote(name=self.name, score=0.0, reason="no PSAR data")

        score = 0.0
        reasons = []

        # Current position relative to SAR
        bullish = close > psar
        if bullish:
            score += 0.3
            reasons.append("price above PSAR (bullish)")
        else:
            score -= 0.3
            reasons.append("price below PSAR (bearish)")

        # SAR flip detection
        if prev_features:
            prev_close = prev_features.get("close", 0)
            prev_psar = prev_features.get("psar", 0)
            if prev_psar and prev_close:
                prev_bullish = prev_close > prev_psar
                if not prev_bullish and bullish:
                    score += 0.5
                    reasons.append("PSAR flipped bullish")
                elif prev_bullish and not bullish:
                    score -= 0.5
                    reasons.append("PSAR flipped bearish")

        score = max(-1.0, min(1.0, score))
        return StrategyVote(
            name=self.name,
            score=round(score, 3),
            reason="; ".join(reasons) if reasons else "no signal",
        )
