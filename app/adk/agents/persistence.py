import logging
import json
from datetime import datetime
from typing import AsyncGenerator
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions

from app.database import SessionLocal
from app.models import (
    MarketSnapshot, Feature, FeatureExtended, Signal, StrategyVoteRecord,
    LLMDecision, RiskCheck, Order, Position, PortfolioSnapshot,
)
from app.services.portfolio_manager import calculate_portfolio_snapshot

logger = logging.getLogger(__name__)

# Will be set by main.py startup
ws_manager = None


def set_ws_manager(manager):
    global ws_manager
    ws_manager = manager


class PersistenceAgent(BaseAgent):
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        agent_config = state.get("agent_config", {})
        agent_id = agent_config.get("id", 1)

        if state.get("tick_error"):
            await self._broadcast({
                "type": "error",
                "data": {"error": state["tick_error"], "agent_id": agent_id},
            })
            yield Event(author=self.name, actions=EventActions(state_delta={"tick_error": state["tick_error"]}))
            return

        db = SessionLocal()
        try:
            # Save market snapshot (latest candle)
            ohlcv = state.get("ohlcv_data", {})
            if ohlcv and ohlcv.get("close"):
                idx = len(ohlcv["close"]) - 1
                timestamps = state.get("ohlcv_timestamps", [])
                ts = datetime.fromisoformat(timestamps[idx]) if timestamps else datetime.now()
                snapshot = MarketSnapshot(
                    agent_id=agent_id,
                    timestamp=ts,
                    open=ohlcv["open"][idx],
                    high=ohlcv["high"][idx],
                    low=ohlcv["low"][idx],
                    close=ohlcv["close"][idx],
                    volume=ohlcv["volume"][idx],
                )
                db.add(snapshot)

            # Save basic features
            features = state.get("features")
            if features:
                db.add(Feature(
                    agent_id=agent_id,
                    ema_fast=features.get("ema_fast"),
                    ema_slow=features.get("ema_slow"),
                    rsi=features.get("rsi"),
                    atr=features.get("atr"),
                    close=features.get("close"),
                ))

                # Save extended features
                db.add(FeatureExtended(
                    agent_id=agent_id,
                    ema_9=features.get("ema_9"),
                    ema_21=features.get("ema_21"),
                    ema_50=features.get("ema_50"),
                    rsi=features.get("rsi"),
                    stoch_k=features.get("stoch_k"),
                    stoch_d=features.get("stoch_d"),
                    macd_line=features.get("macd_line"),
                    macd_signal=features.get("macd_signal"),
                    macd_hist=features.get("macd_hist"),
                    atr=features.get("atr"),
                    bb_upper=features.get("bb_upper"),
                    bb_middle=features.get("bb_middle"),
                    bb_lower=features.get("bb_lower"),
                    bb_width=features.get("bb_width"),
                    bb_pct=features.get("bb_pct"),
                    psar=features.get("psar"),
                    adx=features.get("adx"),
                    plus_di=features.get("plus_di"),
                    minus_di=features.get("minus_di"),
                    donchian_high=features.get("donchian_high"),
                    donchian_low=features.get("donchian_low"),
                    obv=features.get("obv"),
                    obv_delta=features.get("obv_delta"),
                    vol_sma_20=features.get("vol_sma_20"),
                    vol_ratio=features.get("vol_ratio"),
                    fib_382=features.get("fib_382"),
                    fib_500=features.get("fib_500"),
                    fib_618=features.get("fib_618"),
                    fib_proximity=features.get("fib_proximity"),
                    close=features.get("close"),
                ))

            # Save signal
            signal = state.get("signal")
            signal_id = None
            if signal:
                sig = Signal(
                    agent_id=agent_id,
                    direction=signal["direction"],
                    confidence=signal["confidence"],
                    reason=signal["reason"],
                    ensemble_score=signal.get("ensemble_score"),
                )
                db.add(sig)
                db.flush()
                signal_id = sig.id

            # Save strategy votes
            strategy_votes = state.get("strategy_votes", [])
            if strategy_votes and signal_id:
                for vote in strategy_votes:
                    db.add(StrategyVoteRecord(
                        agent_id=agent_id,
                        signal_id=signal_id,
                        strategy_name=vote["name"],
                        score=vote["score"],
                        weight=vote.get("weight", 1.0),
                        reason=vote.get("reason", ""),
                    ))

            # Save LLM decision
            llm_raw = state.get("llm_reasoning")
            if llm_raw and signal_id:
                llm_data = {}
                if isinstance(llm_raw, str):
                    try:
                        llm_data = json.loads(llm_raw)
                    except json.JSONDecodeError:
                        llm_data = {"reasoning": llm_raw}
                elif isinstance(llm_raw, dict):
                    llm_data = llm_raw

                db.add(LLMDecision(
                    agent_id=agent_id,
                    signal_id=signal_id,
                    model_used=agent_config.get("llm_model", "unknown"),
                    reasoning=llm_data.get("reasoning", str(llm_raw)),
                    recommendation=llm_data.get("recommendation", ""),
                    confidence_adjustment=llm_data.get("confidence_adjustment", 0.0),
                ))

            # Save risk check
            risk = state.get("risk_approval")
            if risk and signal_id:
                db.add(RiskCheck(
                    agent_id=agent_id,
                    signal_id=signal_id,
                    approved=risk["approved"],
                    max_trade_ok=risk.get("max_trade_ok", True),
                    max_position_ok=risk.get("max_position_ok", True),
                    drawdown_ok=risk.get("drawdown_ok", True),
                    daily_loss_ok=risk.get("daily_loss_ok", True),
                    cooldown_ok=risk.get("cooldown_ok", True),
                    consecutive_loss_ok=risk.get("consecutive_loss_ok", True),
                    data_complete_ok=risk.get("data_complete_ok", True),
                    rejection_reason=risk.get("rejection_reason"),
                ))

            # Save trade / order
            trade = state.get("trade_result")
            if trade and signal_id:
                db.add(Order(
                    agent_id=agent_id,
                    signal_id=signal_id,
                    side=trade["side"],
                    quantity=trade["quantity"],
                    price=trade["price"],
                    fee=trade["fee"],
                    slippage=trade["slippage"],
                    total_cost=trade["total_cost"],
                    status=trade["status"],
                    mode=trade["mode"],
                ))

                # Update recent_orders in state (keep last 10)
                recent = list(state.get("recent_orders", []))
                recent.append({
                    "side": trade["side"],
                    "quantity": trade["quantity"],
                    "price": trade["price"],
                    "fee": trade["fee"],
                    "total_cost": trade["total_cost"],
                    "status": trade["status"],
                    "mode": trade["mode"],
                    "created_at": datetime.now().isoformat(),
                })
                state["recent_orders"] = recent[-10:]

            # Update position
            portfolio = state.get("portfolio", {})
            pos = db.query(Position).filter(Position.agent_id == agent_id).first()
            current_price = state.get("current_price", 0)
            if pos:
                pos.side = portfolio.get("side", "flat")
                pos.entry_price = portfolio.get("entry_price", 0)
                pos.quantity = portfolio.get("position_qty", 0)
                pos.unrealized_pnl = (current_price - pos.entry_price) * pos.quantity if pos.quantity > 0 else 0
            else:
                db.add(Position(
                    agent_id=agent_id,
                    side=portfolio.get("side", "flat"),
                    entry_price=portfolio.get("entry_price", 0),
                    quantity=portfolio.get("position_qty", 0),
                ))

            # Save portfolio snapshot
            budget = agent_config.get("budget_usd", 100.0)
            snap = calculate_portfolio_snapshot(portfolio, current_price, budget)
            # Update state with calculated values
            portfolio["max_drawdown"] = snap["max_drawdown"]
            portfolio["peak_equity"] = snap["peak_equity"]
            state["portfolio"] = portfolio

            db.add(PortfolioSnapshot(
                agent_id=agent_id,
                cash=snap["cash"],
                equity=snap["equity"],
                total_pnl=snap["total_pnl"],
                total_pnl_pct=snap["total_pnl_pct"],
                win_count=snap["win_count"],
                loss_count=snap["loss_count"],
                total_trades=snap["total_trades"],
                max_drawdown=snap["max_drawdown"],
            ))

            db.commit()

            # RL incremental update after trade
            if trade and agent_config.get("enable_rl") and features:
                self._rl_update(agent_id, features, trade, budget)

            # Broadcast WebSocket update
            ws_data = {
                "type": "tick",
                "data": {
                    "agent_id": agent_id,
                    "price": current_price,
                    "features": features,
                    "signal": signal,
                    "risk": risk,
                    "trade": trade,
                    "portfolio": snap,
                    "llm_reasoning": state.get("llm_reasoning"),
                    "sl_tp": state.get("sl_tp"),
                    "ensemble_score": signal.get("ensemble_score") if signal else None,
                    "timestamp": datetime.now().isoformat(),
                },
            }
            await self._broadcast(ws_data)

        except Exception as e:
            db.rollback()
            logger.error(f"Persistence failed: {e}")
        finally:
            db.close()

        delta = {
            "portfolio": state.get("portfolio"),
            "recent_orders": state.get("recent_orders"),
        }
        yield Event(author=self.name, actions=EventActions(state_delta=delta))

    def _rl_update(self, agent_id: int, features: dict, trade: dict, budget: float):
        """Incremental RL Q-table update after a trade."""
        try:
            from app.services.rl.model_store import ModelStore
            from app.services.rl.q_learning import QLearningAgent

            rl_agent = ModelStore.load(agent_id)
            if not rl_agent:
                return

            action = rl_agent.direction_to_action(trade["side"].upper())
            reward = trade.get("realized_pnl", 0) / budget if budget > 0 else 0
            rl_agent.update(features, action, reward, features)
            ModelStore.save(agent_id, rl_agent)
        except Exception as e:
            logger.warning(f"[RL] Incremental update failed: {e}")

    @staticmethod
    def _sanitize_for_json(obj):
        """Recursively convert NaN/Infinity to None and numpy types to Python types."""
        import math
        if isinstance(obj, dict):
            return {k: PersistenceAgent._sanitize_for_json(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [PersistenceAgent._sanitize_for_json(v) for v in obj]
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        # Handle numpy scalar types
        type_name = type(obj).__module__
        if type_name == "numpy":
            try:
                val = float(obj)
                if math.isnan(val) or math.isinf(val):
                    return None
                return val
            except (TypeError, ValueError):
                return str(obj)
        return obj

    async def _broadcast(self, data: dict):
        if ws_manager:
            clean = self._sanitize_for_json(data)
            await ws_manager.broadcast(json.dumps(clean))
