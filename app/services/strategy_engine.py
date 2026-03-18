import logging

from app.services.strategies import STRATEGY_REGISTRY, StrategyVote

logger = logging.getLogger(__name__)

# Thresholds for ensemble signal
BUY_THRESHOLD = 0.25
SELL_THRESHOLD = -0.25


def evaluate_trend_following(
    features: dict, prev_features: dict | None, params: dict | None = None
) -> dict:
    """Backward-compatible wrapper that calls the ensemble."""
    return evaluate_ensemble(features, prev_features, params)


def evaluate_ensemble(
    features: dict,
    prev_features: dict | None = None,
    params: dict | None = None,
) -> dict:
    """Multi-strategy ensemble with weighted voting.

    Each sub-strategy votes between -1.0 (SELL) and +1.0 (BUY).
    Weighted average determines final signal.
    """
    if not features:
        return {
            "direction": "HOLD",
            "confidence": 0.0,
            "reason": "No features available",
            "votes": [],
        }

    # Get custom weights from agent config
    custom_weights = (params or {}).get("strategy_weights", {})
    rsi_buy_max = (params or {}).get("rsi_buy_max", 70.0)
    rsi_sell_min = (params or {}).get("rsi_sell_min", 30.0)

    votes: list[StrategyVote] = []
    total_weight = 0.0
    weighted_sum = 0.0

    for strategy in STRATEGY_REGISTRY:
        try:
            vote = strategy.evaluate(features, prev_features, params)
            # Apply custom weight override if available
            weight = custom_weights.get(strategy.name, strategy.default_weight)
            vote.weight = weight

            votes.append(vote)
            weighted_sum += vote.score * weight
            total_weight += weight
        except Exception as e:
            logger.warning(f"Strategy {strategy.name} failed: {e}")

    if total_weight == 0:
        return {
            "direction": "HOLD",
            "confidence": 0.0,
            "reason": "No strategies produced votes",
            "votes": [],
        }

    ensemble_score = weighted_sum / total_weight

    # RSI filter (same as original but softer — reduces confidence instead of blocking)
    rsi = features.get("rsi", 50)
    rsi_penalty = 0.0
    if ensemble_score > 0 and rsi > rsi_buy_max:
        rsi_penalty = min(0.3, (rsi - rsi_buy_max) / 30)
        ensemble_score -= rsi_penalty
    elif ensemble_score < 0 and rsi < rsi_sell_min:
        rsi_penalty = min(0.3, (rsi_sell_min - rsi) / 30)
        ensemble_score += rsi_penalty

    # Determine direction
    if ensemble_score > BUY_THRESHOLD:
        direction = "BUY"
        confidence = min(0.95, abs(ensemble_score))
    elif ensemble_score < SELL_THRESHOLD:
        direction = "SELL"
        confidence = min(0.95, abs(ensemble_score))
    else:
        direction = "HOLD"
        confidence = 0.0

    # Build reason from top contributing votes
    active_votes = sorted(votes, key=lambda v: abs(v.score), reverse=True)
    top_reasons = [f"{v.name}={v.score:+.2f}" for v in active_votes[:4] if v.score != 0]
    reason = f"Ensemble={ensemble_score:+.3f} [{', '.join(top_reasons)}]"
    if rsi_penalty > 0:
        reason += f" RSI penalty={rsi_penalty:.2f}"

    # Serialize votes for transparency
    votes_data = [
        {"name": v.name, "score": v.score, "weight": v.weight, "reason": v.reason}
        for v in votes
    ]

    return {
        "direction": direction,
        "confidence": round(confidence, 3),
        "reason": reason,
        "ensemble_score": round(ensemble_score, 4),
        "votes": votes_data,
    }
