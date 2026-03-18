from abc import ABC, abstractmethod
import pandas as pd


class BaseIndicator(ABC):
    """Base class for all technical indicators."""

    name: str = ""

    @abstractmethod
    def calculate(self, df: pd.DataFrame) -> dict[str, float]:
        """Calculate indicator values from OHLCV DataFrame.

        Returns dict of {indicator_name: value} for the latest bar.
        """
        ...
