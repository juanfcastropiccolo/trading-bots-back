from app.services.strategies.base import BaseStrategy, StrategyVote


class VolumeConfirmationStrategy(BaseStrategy):
    name = "volume_confirmation"
    default_weight = 0.8

    def evaluate(self, features: dict, prev_features: dict | None = None, params: dict | None = None) -> StrategyVote:
        obv_delta = features.get("obv_delta", 0)
        vol_ratio = features.get("vol_ratio", 1.0)
        close = features.get("close", 0)

        score = 0.0
        reasons = []

        # OBV trend confirmation
        if obv_delta > 0:
            score += 0.3
            reasons.append("OBV rising")
        elif obv_delta < 0:
            score -= 0.3
            reasons.append("OBV falling")

        # Volume spike (ratio > 1.5x average)
        if vol_ratio > 2.0:
            # Big volume spike — amplify existing direction
            if prev_features:
                prev_close = prev_features.get("close", close)
                if close > prev_close:
                    score += 0.4
                    reasons.append(f"volume spike ({vol_ratio:.1f}x) on up move")
                elif close < prev_close:
                    score -= 0.4
                    reasons.append(f"volume spike ({vol_ratio:.1f}x) on down move")
        elif vol_ratio > 1.5:
            if prev_features:
                prev_close = prev_features.get("close", close)
                if close > prev_close:
                    score += 0.2
                    reasons.append(f"above-avg volume ({vol_ratio:.1f}x) on up")
                elif close < prev_close:
                    score -= 0.2
                    reasons.append(f"above-avg volume ({vol_ratio:.1f}x) on down")

        score = max(-1.0, min(1.0, score))
        return StrategyVote(
            name=self.name,
            score=round(score, 3),
            reason="; ".join(reasons) if reasons else "no signal",
        )
