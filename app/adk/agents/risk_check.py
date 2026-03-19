import json
import logging
from typing import AsyncGenerator
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions

from app.services.risk_manager import check_risk

logger = logging.getLogger(__name__)


class RiskCheckAgent(BaseAgent):
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        if ctx.session.state.get("tick_error"):
            yield Event(author=self.name)
            return

        signal = ctx.session.state.get("signal")
        if not signal:
            yield Event(author=self.name)
            return

        features = ctx.session.state.get("features")
        portfolio = ctx.session.state.get("portfolio", {})
        agent_config = ctx.session.state.get("agent_config", {})
        recent_orders = ctx.session.state.get("recent_orders", [])

        # Apply LLM confidence adjustment
        llm_raw = ctx.session.state.get("llm_reasoning")
        llm_adjustment = 0.0
        llm_sl_mult = None
        llm_tp_mult = None
        if llm_raw:
            llm_data = self._parse_llm(llm_raw)
            llm_adjustment = max(-0.3, min(0.3, llm_data.get("confidence_adjustment", 0.0)))
            llm_sl_mult = llm_data.get("suggested_sl_mult")
            llm_tp_mult = llm_data.get("suggested_tp_mult")

            # Adjust signal confidence
            original_conf = signal.get("confidence", 0.0)
            adjusted_conf = max(0.0, min(0.95, original_conf + llm_adjustment))
            signal["confidence"] = round(adjusted_conf, 3)
            signal["llm_adjustment"] = llm_adjustment
            ctx.session.state["signal"] = signal

            if llm_adjustment != 0:
                logger.info(f"LLM adjusted confidence: {original_conf:.3f} -> {adjusted_conf:.3f} (adj={llm_adjustment:+.3f})")

        # Store SL/TP parameters for execution engine
        atr = features.get("atr", 0) if features else 0
        current_price = ctx.session.state.get("current_price", 0)
        sl_mult = llm_sl_mult if llm_sl_mult else agent_config.get("stop_loss_atr_mult", 2.0)
        tp_mult = llm_tp_mult if llm_tp_mult else agent_config.get("take_profit_atr_mult", 3.0)

        ctx.session.state["sl_tp"] = {
            "stop_loss": round(current_price - atr * sl_mult, 2) if atr else None,
            "take_profit": round(current_price + atr * tp_mult, 2) if atr else None,
            "sl_mult": sl_mult,
            "tp_mult": tp_mult,
        }

        risk_result = check_risk(signal, features, portfolio, agent_config, recent_orders)

        # Check SL/TP triggers (checks 8 & 9)
        entry_price = portfolio.get("entry_price", 0)
        position_qty = portfolio.get("position_qty", 0)
        if position_qty > 0 and atr > 0 and entry_price > 0:
            sl_price = entry_price - atr * sl_mult
            tp_price = entry_price + atr * tp_mult

            if current_price <= sl_price:
                # Force SELL — stop loss triggered
                risk_result["approved"] = True
                risk_result["rejection_reason"] = None
                signal["direction"] = "SELL"
                signal["confidence"] = 0.95
                signal["reason"] = f"STOP LOSS triggered: price {current_price} <= SL {sl_price:.2f} (entry {entry_price} - {sl_mult}×ATR)"
                ctx.session.state["signal"] = signal
                logger.warning(f"STOP LOSS triggered at {current_price}")

            elif current_price >= tp_price:
                # Force SELL — take profit triggered
                risk_result["approved"] = True
                risk_result["rejection_reason"] = None
                signal["direction"] = "SELL"
                signal["confidence"] = 0.90
                signal["reason"] = f"TAKE PROFIT triggered: price {current_price} >= TP {tp_price:.2f} (entry {entry_price} + {tp_mult}×ATR)"
                ctx.session.state["signal"] = signal
                logger.info(f"TAKE PROFIT triggered at {current_price}")

        ctx.session.state["risk_approval"] = risk_result

        if risk_result["approved"]:
            logger.info("Risk check APPROVED")
        else:
            logger.info(f"Risk check REJECTED: {risk_result['rejection_reason']}")

        delta = {
            "risk_approval": ctx.session.state.get("risk_approval"),
            "signal": ctx.session.state.get("signal"),
            "sl_tp": ctx.session.state.get("sl_tp"),
        }
        yield Event(author=self.name, actions=EventActions(state_delta=delta))

    def _parse_llm(self, llm_raw) -> dict:
        if isinstance(llm_raw, dict):
            return llm_raw
        if isinstance(llm_raw, str):
            try:
                return json.loads(llm_raw)
            except json.JSONDecodeError:
                return {}
        return {}
