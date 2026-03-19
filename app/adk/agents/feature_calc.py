import logging
from typing import AsyncGenerator
import pandas as pd
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions

from app.services.feature_engine import calculate_features_extended

logger = logging.getLogger(__name__)


class FeatureCalcAgent(BaseAgent):
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        if ctx.session.state.get("tick_error"):
            yield Event(author=self.name)
            return

        ohlcv_data = ctx.session.state.get("ohlcv_data")
        if not ohlcv_data:
            ctx.session.state["tick_error"] = "No OHLCV data available"
            yield Event(author=self.name, actions=EventActions(state_delta={"tick_error": "No OHLCV data available"}))
            return

        df = pd.DataFrame(ohlcv_data)
        features = calculate_features_extended(df)

        if features is None:
            ctx.session.state["tick_error"] = "Not enough candles for feature calculation"
            yield Event(author=self.name, actions=EventActions(state_delta={"tick_error": "Not enough candles for feature calculation"}))
            return

        # Carry forward previous features for crossover detection
        current_features = ctx.session.state.get("features")
        if current_features and current_features.get("ema_fast", 0) != 0:
            ctx.session.state["prev_features"] = current_features

        ctx.session.state["features"] = features

        # Calculate 1h features if available (multi-timeframe)
        ohlcv_1h = ctx.session.state.get("ohlcv_1h_data")
        if ohlcv_1h:
            df_1h = pd.DataFrame(ohlcv_1h)
            features_1h = calculate_features_extended(df_1h)
            if features_1h:
                ctx.session.state["features_1h"] = features_1h
                logger.info(f"1h features: EMA9={features_1h.get('ema_fast')}, RSI={features_1h.get('rsi')}")

        logger.info(
            f"Features: EMA9={features['ema_fast']}, EMA21={features['ema_slow']}, "
            f"RSI={features['rsi']}, MACD_hist={features.get('macd_hist', 'N/A')}, "
            f"ADX={features.get('adx', 'N/A')}, BB%={features.get('bb_pct', 'N/A')}"
        )

        state = ctx.session.state
        delta = {
            "features": state.get("features"),
            "prev_features": state.get("prev_features"),
            "features_1h": state.get("features_1h"),
        }
        yield Event(author=self.name, actions=EventActions(state_delta=delta))
