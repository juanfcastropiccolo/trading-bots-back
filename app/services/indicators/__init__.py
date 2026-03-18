from app.services.indicators.base import BaseIndicator
from app.services.indicators.moving_averages import MovingAveragesIndicator
from app.services.indicators.momentum import MomentumIndicator
from app.services.indicators.volatility import VolatilityIndicator
from app.services.indicators.trend import TrendIndicator
from app.services.indicators.volume import VolumeIndicator
from app.services.indicators.levels import FibonacciIndicator

INDICATOR_REGISTRY: list[BaseIndicator] = [
    MovingAveragesIndicator(),
    MomentumIndicator(),
    VolatilityIndicator(),
    TrendIndicator(),
    VolumeIndicator(),
    FibonacciIndicator(),
]

__all__ = ["INDICATOR_REGISTRY", "BaseIndicator"]
