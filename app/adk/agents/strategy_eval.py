import logging
from typing import AsyncGenerator
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event

from app.services.strategy_engine import evaluate_ensemble

logger = logging.getLogger(__name__)


class StrategyEvalAgent(BaseAgent):
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        if ctx.session.state.get("tick_error"):
            yield Event(author=self.name)
            return

        features = ctx.session.state.get("features")
        prev_features = ctx.session.state.get("prev_features")

        if not features:
            ctx.session.state["tick_error"] = "No features available"
            yield Event(author=self.name)
            return

        agent_config = ctx.session.state.get("agent_config", {})
        signal = evaluate_ensemble(features, prev_features, params=agent_config)

        # Multi-timeframe filter: if 1h trend opposes 1m signal, reduce confidence
        features_1h = ctx.session.state.get("features_1h")
        if features_1h and signal["direction"] != "HOLD":
            ema_fast_1h = features_1h.get("ema_fast", 0)
            ema_slow_1h = features_1h.get("ema_slow", 0)
            if ema_fast_1h and ema_slow_1h:
                trend_1h_bullish = ema_fast_1h > ema_slow_1h
                if signal["direction"] == "BUY" and not trend_1h_bullish:
                    signal["confidence"] = round(signal["confidence"] * 0.6, 3)
                    signal["reason"] += " | 1h trend bearish (conf reduced)"
                elif signal["direction"] == "SELL" and trend_1h_bullish:
                    signal["confidence"] = round(signal["confidence"] * 0.6, 3)
                    signal["reason"] += " | 1h trend bullish (conf reduced)"
                else:
                    signal["reason"] += " | 1h trend confirms"

        # RL confidence modifier (if available)
        rl_confidence = ctx.session.state.get("rl_confidence")
        if rl_confidence is not None and signal["direction"] != "HOLD":
            ensemble_conf = signal["confidence"]
            blended = 0.7 * ensemble_conf + 0.3 * rl_confidence
            signal["confidence"] = round(max(0.0, min(0.95, blended)), 3)
            signal["rl_confidence"] = rl_confidence
            signal["reason"] += f" | RL={rl_confidence:.2f}"

        ctx.session.state["signal"] = signal
        ctx.session.state["strategy_votes"] = signal.get("votes", [])

        logger.info(
            f"Signal: {signal['direction']} (confidence={signal['confidence']}, "
            f"ensemble={signal.get('ensemble_score', 'N/A')})"
        )

        yield Event(author=self.name)
