from app.services.strategies.base import BaseStrategy, StrategyVote
from app.services.strategies.ema_crossover import EMACrossoverStrategy
from app.services.strategies.macd_strategy import MACDStrategy
from app.services.strategies.bollinger_strategy import BollingerStrategy
from app.services.strategies.stochastic_strategy import StochasticStrategy
from app.services.strategies.adx_trend import ADXTrendStrategy
from app.services.strategies.volume_confirmation import VolumeConfirmationStrategy
from app.services.strategies.fibonacci_levels import FibonacciLevelsStrategy
from app.services.strategies.parabolic_sar import ParabolicSARStrategy

STRATEGY_REGISTRY: list[BaseStrategy] = [
    EMACrossoverStrategy(),
    MACDStrategy(),
    BollingerStrategy(),
    StochasticStrategy(),
    ADXTrendStrategy(),
    VolumeConfirmationStrategy(),
    FibonacciLevelsStrategy(),
    ParabolicSARStrategy(),
]

__all__ = ["STRATEGY_REGISTRY", "BaseStrategy", "StrategyVote"]
