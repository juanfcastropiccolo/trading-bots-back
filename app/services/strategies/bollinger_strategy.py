from app.services.strategies.base import BaseStrategy, StrategyVote


class BollingerStrategy(BaseStrategy):
    name = "bollinger"
    default_weight = 1.0

    def evaluate(self, features: dict, prev_features: dict | None = None, params: dict | None = None) -> StrategyVote:
        bb_pct = features.get("bb_pct", 0.5)
        bb_width = features.get("bb_width", 0)
        close = features.get("close", 0)
        bb_lower = features.get("bb_lower", 0)
        bb_upper = features.get("bb_upper", 0)

        score = 0.0
        reasons = []

        # Squeeze detection: narrow bands suggest breakout coming
        if bb_width < 0.02:
            # Don't vote direction, just note squeeze
            reasons.append("BB squeeze detected")

        # Mean reversion: price at extremes of bands
        if bb_pct <= 0.0:
            score += 0.6
            reasons.append("price below lower BB (oversold)")
        elif bb_pct <= 0.1:
            score += 0.3
            reasons.append("price near lower BB")
        elif bb_pct >= 1.0:
            score -= 0.6
            reasons.append("price above upper BB (overbought)")
        elif bb_pct >= 0.9:
            score -= 0.3
            reasons.append("price near upper BB")

        # Band walk: persistent trend along band
        if prev_features:
            prev_bb_pct = prev_features.get("bb_pct", 0.5)
            if bb_pct > 0.8 and prev_bb_pct > 0.8:
                score += 0.2
                reasons.append("bullish band walk")
            elif bb_pct < 0.2 and prev_bb_pct < 0.2:
                score -= 0.2
                reasons.append("bearish band walk")

        score = max(-1.0, min(1.0, score))
        return StrategyVote(
            name=self.name,
            score=round(score, 3),
            reason="; ".join(reasons) if reasons else "no signal",
        )
