import logging
from datetime import datetime

from app.database import SessionLocal
from app.models import Feature, Order, PortfolioSnapshot
from app.services.rl.q_learning import QLearningAgent

logger = logging.getLogger(__name__)


class RLTrainer:
    """Train Q-Learning agent from historical data in DB."""

    def __init__(self, agent_id: int):
        self.agent_id = agent_id
        self.rl_agent = QLearningAgent()

    def train_from_history(self, epochs: int = 5) -> QLearningAgent:
        """Batch training from stored features and trade outcomes."""
        db = SessionLocal()
        try:
            # Load features ordered by time
            features_rows = (
                db.query(Feature)
                .filter(Feature.agent_id == self.agent_id)
                .order_by(Feature.id.asc())
                .all()
            )

            if len(features_rows) < 10:
                logger.info(f"[RL] Agent {self.agent_id}: not enough data ({len(features_rows)} rows)")
                return self.rl_agent

            # Load orders to build reward mapping
            orders = (
                db.query(Order)
                .filter(Order.agent_id == self.agent_id)
                .order_by(Order.id.asc())
                .all()
            )

            # Load budget for normalization
            snap = (
                db.query(PortfolioSnapshot)
                .filter(PortfolioSnapshot.agent_id == self.agent_id)
                .order_by(PortfolioSnapshot.id.desc())
                .first()
            )
            budget = snap.equity if snap else 100.0

            # Build order timeline (map created_at to realized_pnl)
            order_rewards = {}
            for order in orders:
                if order.side == "sell":
                    # Find the pnl from the order's associated signal
                    order_rewards[order.created_at] = getattr(order, "total_cost", 0)

            logger.info(
                f"[RL] Training agent {self.agent_id}: {len(features_rows)} features, "
                f"{len(orders)} orders, {epochs} epochs"
            )

            for epoch in range(epochs):
                total_reward = 0.0
                for i in range(len(features_rows) - 1):
                    feat = features_rows[i]
                    next_feat = features_rows[i + 1]

                    state = self._feature_to_dict(feat)
                    next_state = self._feature_to_dict(next_feat)

                    # Determine what action was taken (from orders near this timestamp)
                    action = 0  # Default: HOLD

                    # Simple reward: price change as proxy
                    if next_feat.close and feat.close and feat.close > 0:
                        price_change = (next_feat.close - feat.close) / feat.close
                        # Reward based on holding position or being flat
                        reward = price_change * 10  # Scale for Q-learning
                    else:
                        reward = 0.0

                    total_reward += reward
                    self.rl_agent.update(state, action, reward, next_state)

                logger.info(f"[RL] Epoch {epoch + 1}/{epochs}: total_reward={total_reward:.4f}")

            return self.rl_agent

        except Exception as e:
            logger.error(f"[RL] Training failed: {e}", exc_info=True)
            return self.rl_agent
        finally:
            db.close()

    def _feature_to_dict(self, feat: Feature) -> dict:
        """Convert Feature ORM row to dict for discretizer."""
        return {
            "ema_fast": feat.ema_fast or 0,
            "ema_slow": feat.ema_slow or 0,
            "rsi": feat.rsi or 50,
            "atr": feat.atr or 0,
            "close": feat.close or 0,
            "macd_hist": 0,  # Not stored in basic features table
            "adx": 25,  # Default mid-range
            "bb_pct": 0.5,  # Default mid-range
        }
