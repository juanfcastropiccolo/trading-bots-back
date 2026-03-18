from app.services.strategies.base import BaseStrategy, StrategyVote


class StochasticStrategy(BaseStrategy):
    name = "stochastic"
    default_weight = 1.0

    def evaluate(self, features: dict, prev_features: dict | None = None, params: dict | None = None) -> StrategyVote:
        stoch_k = features.get("stoch_k", 50)
        stoch_d = features.get("stoch_d", 50)

        score = 0.0
        reasons = []

        # %K/%D crossover in OB/OS zones
        if prev_features:
            prev_k = prev_features.get("stoch_k", 50)
            prev_d = prev_features.get("stoch_d", 50)

            bullish_cross = prev_k <= prev_d and stoch_k > stoch_d
            bearish_cross = prev_k >= prev_d and stoch_k < stoch_d

            # Oversold zone crossover (< 20)
            if bullish_cross and stoch_k < 30:
                score += 0.7
                reasons.append(f"bullish stoch crossover in OS zone (K={stoch_k:.0f})")
            elif bullish_cross:
                score += 0.3
                reasons.append(f"bullish stoch crossover (K={stoch_k:.0f})")

            # Overbought zone crossover (> 80)
            if bearish_cross and stoch_k > 70:
                score -= 0.7
                reasons.append(f"bearish stoch crossover in OB zone (K={stoch_k:.0f})")
            elif bearish_cross:
                score -= 0.3
                reasons.append(f"bearish stoch crossover (K={stoch_k:.0f})")

        # Extreme zones without crossover
        if stoch_k < 15:
            score += 0.2
            reasons.append("deeply oversold")
        elif stoch_k > 85:
            score -= 0.2
            reasons.append("deeply overbought")

        score = max(-1.0, min(1.0, score))
        return StrategyVote(
            name=self.name,
            score=round(score, 3),
            reason="; ".join(reasons) if reasons else "no signal",
        )
