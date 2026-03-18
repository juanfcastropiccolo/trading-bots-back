from app.services.strategies.base import BaseStrategy, StrategyVote


class EMACrossoverStrategy(BaseStrategy):
    name = "ema_crossover"
    default_weight = 1.5

    def evaluate(self, features: dict, prev_features: dict | None = None, params: dict | None = None) -> StrategyVote:
        ema_9 = features.get("ema_9", features.get("ema_fast", 0))
        ema_21 = features.get("ema_21", features.get("ema_slow", 0))
        ema_50 = features.get("ema_50", 0)

        if not prev_features:
            return StrategyVote(name=self.name, score=0.0, reason="No prev data")

        prev_ema_9 = prev_features.get("ema_9", prev_features.get("ema_fast", 0))
        prev_ema_21 = prev_features.get("ema_21", prev_features.get("ema_slow", 0))

        score = 0.0
        reasons = []

        # Crossover detection (+/- 0.8)
        bullish_cross = prev_ema_9 <= prev_ema_21 and ema_9 > ema_21
        bearish_cross = prev_ema_9 >= prev_ema_21 and ema_9 < ema_21

        if bullish_cross:
            score += 0.8
            reasons.append("bullish EMA 9/21 crossover")
        elif bearish_cross:
            score -= 0.8
            reasons.append("bearish EMA 9/21 crossover")

        # EMA alignment bonus (+/- 0.3)
        if ema_9 > ema_21 > ema_50 > 0:
            score += 0.3
            reasons.append("bullish EMA alignment 9>21>50")
        elif ema_9 < ema_21 < ema_50 and ema_50 > 0:
            score -= 0.3
            reasons.append("bearish EMA alignment 9<21<50")

        # Proximity bonus: if close to crossover (+/- 0.2)
        if ema_21 > 0:
            spread_pct = (ema_9 - ema_21) / ema_21 * 100
            if 0 < spread_pct < 0.05:
                score += 0.2
                reasons.append("near bullish crossover")
            elif -0.05 < spread_pct < 0:
                score -= 0.2
                reasons.append("near bearish crossover")

        score = max(-1.0, min(1.0, score))
        return StrategyVote(
            name=self.name,
            score=round(score, 3),
            reason="; ".join(reasons) if reasons else "no signal",
        )
