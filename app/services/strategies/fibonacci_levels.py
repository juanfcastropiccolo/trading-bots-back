from app.services.strategies.base import BaseStrategy, StrategyVote


class FibonacciLevelsStrategy(BaseStrategy):
    name = "fibonacci_levels"
    default_weight = 0.8

    def evaluate(self, features: dict, prev_features: dict | None = None, params: dict | None = None) -> StrategyVote:
        close = features.get("close", 0)
        fib_382 = features.get("fib_382", 0)
        fib_500 = features.get("fib_500", 0)
        fib_618 = features.get("fib_618", 0)
        fib_proximity = features.get("fib_proximity", 1.0)
        atr = features.get("atr", 0)

        if not close or not atr or atr == 0:
            return StrategyVote(name=self.name, score=0.0, reason="insufficient data")

        score = 0.0
        reasons = []

        # Check bounce off Fib levels (within 0.5 ATR)
        threshold = atr * 0.5

        for level, name in [(fib_382, "38.2%"), (fib_500, "50%"), (fib_618, "61.8%")]:
            dist = close - level
            if abs(dist) < threshold:
                if prev_features:
                    prev_close = prev_features.get("close", 0)
                    # Bounce up from support
                    if prev_close < level and close >= level:
                        score += 0.5
                        reasons.append(f"bounce up from Fib {name}")
                    # Bounce down from resistance
                    elif prev_close > level and close <= level:
                        score -= 0.5
                        reasons.append(f"rejection at Fib {name}")
                else:
                    # Near a level = potential support/resistance
                    if dist > 0:
                        score += 0.2
                        reasons.append(f"above Fib {name} support")
                    else:
                        score -= 0.2
                        reasons.append(f"below Fib {name} resistance")

        score = max(-1.0, min(1.0, score))
        return StrategyVote(
            name=self.name,
            score=round(score, 3),
            reason="; ".join(reasons) if reasons else "no Fib signal",
        )
