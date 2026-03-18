from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class StrategyVote:
    """A strategy's vote: score from -1.0 (strong SELL) to +1.0 (strong BUY)."""
    name: str
    score: float  # -1.0 to +1.0
    reason: str
    weight: float = 1.0


class BaseStrategy(ABC):
    """Base class for all sub-strategies in the ensemble."""

    name: str = ""
    default_weight: float = 1.0

    @abstractmethod
    def evaluate(self, features: dict, prev_features: dict | None = None, params: dict | None = None) -> StrategyVote:
        """Evaluate and return a vote."""
        ...
