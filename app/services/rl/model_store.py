import json
import logging
from datetime import datetime

from app.database import SessionLocal
from app.services.rl.q_learning import QLearningAgent

logger = logging.getLogger(__name__)


class ModelStore:
    """Persist and load RL models from database."""

    @staticmethod
    def save(agent_id: int, rl_agent: QLearningAgent, metadata: dict | None = None):
        """Save Q-table to rl_models table."""
        db = SessionLocal()
        try:
            from app.models import RLModel
            model_data = rl_agent.get_q_table_bytes()

            existing = (
                db.query(RLModel)
                .filter(RLModel.agent_id == agent_id, RLModel.model_type == "q_learning")
                .first()
            )

            meta = json.dumps(metadata or {
                "alpha": rl_agent.alpha,
                "gamma": rl_agent.gamma,
                "epsilon": rl_agent.epsilon,
                "trained_at": datetime.now().isoformat(),
            })

            if existing:
                existing.model_data = model_data
                existing.metadata_json = meta
            else:
                db.add(RLModel(
                    agent_id=agent_id,
                    model_type="q_learning",
                    model_data=model_data,
                    metadata_json=meta,
                ))

            db.commit()
            logger.info(f"[RL] Saved model for agent {agent_id}")
        except Exception as e:
            db.rollback()
            logger.error(f"[RL] Save failed: {e}")
        finally:
            db.close()

    @staticmethod
    def load(agent_id: int) -> QLearningAgent | None:
        """Load Q-table from DB."""
        db = SessionLocal()
        try:
            from app.models import RLModel
            model = (
                db.query(RLModel)
                .filter(RLModel.agent_id == agent_id, RLModel.model_type == "q_learning")
                .first()
            )
            if model and model.model_data:
                rl_agent = QLearningAgent()
                rl_agent.load_q_table_bytes(model.model_data)
                logger.info(f"[RL] Loaded model for agent {agent_id}")
                return rl_agent
        except Exception as e:
            logger.warning(f"[RL] Load failed (table may not exist yet): {e}")
        finally:
            db.close()
        return None
