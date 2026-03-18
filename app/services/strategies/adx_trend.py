from app.services.strategies.base import BaseStrategy, StrategyVote


class ADXTrendStrategy(BaseStrategy):
    name = "adx_trend"
    default_weight = 1.0

    def evaluate(self, features: dict, prev_features: dict | None = None, params: dict | None = None) -> StrategyVote:
        adx = features.get("adx", 0)
        plus_di = features.get("plus_di", 0)
        minus_di = features.get("minus_di", 0)

        score = 0.0
        reasons = []

        # ADX > 25 = trending market
        if adx > 25:
            if plus_di > minus_di:
                strength = min(0.6, (adx - 25) / 50)
                score += strength
                reasons.append(f"trending bullish (ADX={adx:.0f}, +DI>{'-'}DI)")
            else:
                strength = min(0.6, (adx - 25) / 50)
                score -= strength
                reasons.append(f"trending bearish (ADX={adx:.0f}, -DI>+DI)")

            # DI crossover
            if prev_features:
                prev_plus = prev_features.get("plus_di", 0)
                prev_minus = prev_features.get("minus_di", 0)
                if prev_plus <= prev_minus and plus_di > minus_di:
                    score += 0.4
                    reasons.append("+DI crossed above -DI")
                elif prev_plus >= prev_minus and plus_di < minus_di:
                    score -= 0.4
                    reasons.append("-DI crossed above +DI")
        else:
            reasons.append(f"ranging market (ADX={adx:.0f})")

        score = max(-1.0, min(1.0, score))
        return StrategyVote(
            name=self.name,
            score=round(score, 3),
            reason="; ".join(reasons) if reasons else "no signal",
        )
