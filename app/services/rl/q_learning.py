import numpy as np
import logging

from app.services.rl.feature_discretizer import FeatureDiscretizer

logger = logging.getLogger(__name__)


class QLearningAgent:
    """Tabular Q-Learning agent for trading decisions.

    Actions: 0=HOLD, 1=BUY, 2=SELL
    """

    def __init__(
        self,
        alpha: float = 0.1,
        gamma: float = 0.95,
        epsilon: float = 0.1,
    ):
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.discretizer = FeatureDiscretizer()
        self.q_table = np.zeros(
            (FeatureDiscretizer.N_STATES, FeatureDiscretizer.N_ACTIONS),
            dtype=np.float64,
        )

    def get_action(self, features: dict, explore: bool = False) -> int:
        """Choose action using epsilon-greedy policy."""
        state = self.discretizer.discretize(features)
        if explore and np.random.random() < self.epsilon:
            return np.random.randint(0, FeatureDiscretizer.N_ACTIONS)
        return int(np.argmax(self.q_table[state]))

    def get_confidence(self, features: dict) -> float:
        """Get confidence for the best action (normalized Q-value)."""
        state = self.discretizer.discretize(features)
        q_values = self.q_table[state]
        best_q = float(np.max(q_values))

        # Normalize: map Q-value range to 0-1
        q_range = float(np.max(self.q_table) - np.min(self.q_table))
        if q_range > 0:
            return max(0.0, min(1.0, (best_q - np.min(self.q_table)) / q_range))
        return 0.5

    def update(
        self,
        state_features: dict,
        action: int,
        reward: float,
        next_state_features: dict,
        done: bool = False,
    ):
        """Single Q-learning update step."""
        state = self.discretizer.discretize(state_features)
        next_state = self.discretizer.discretize(next_state_features)

        current_q = self.q_table[state, action]
        if done:
            target = reward
        else:
            target = reward + self.gamma * np.max(self.q_table[next_state])

        self.q_table[state, action] += self.alpha * (target - current_q)

    def action_to_direction(self, action: int) -> str:
        return {0: "HOLD", 1: "BUY", 2: "SELL"}.get(action, "HOLD")

    def direction_to_action(self, direction: str) -> int:
        return {"HOLD": 0, "BUY": 1, "SELL": 2}.get(direction, 0)

    def get_q_table_bytes(self) -> bytes:
        """Serialize Q-table to bytes for storage."""
        return self.q_table.tobytes()

    def load_q_table_bytes(self, data: bytes):
        """Load Q-table from bytes."""
        self.q_table = np.frombuffer(data, dtype=np.float64).reshape(
            FeatureDiscretizer.N_STATES, FeatureDiscretizer.N_ACTIONS
        ).copy()
