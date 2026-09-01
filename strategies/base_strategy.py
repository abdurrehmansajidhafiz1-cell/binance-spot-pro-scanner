"""
Abstract Base Strategy Class.
Standardized interface for all Binance Spot strategies.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import pandas as pd


class Signal:
    def __init__(self, symbol: str, action: str, price: float, stop_loss: float,
                 tp1: float, tp2: float, strategy_name: str, reason: str, metadata: Optional[Dict] = None):
        self.symbol = symbol
        self.action = action  # "BUY", "SELL", "HOLD"
        self.price = price
        self.stop_loss = stop_loss
        self.tp1 = tp1
        self.tp2 = tp2
        self.strategy_name = strategy_name
        self.reason = reason
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "action": self.action,
            "price": self.price,
            "stop_loss": self.stop_loss,
            "tp1": self.tp1,
            "tp2": self.tp2,
            "strategy_name": self.strategy_name,
            "reason": self.reason,
            "metadata": self.metadata
        }


class BaseStrategy(ABC):
    def __init__(self, name: str, timeframe: str):
        self.name = name
        self.timeframe = timeframe

    @abstractmethod
    def evaluate(self, symbol: str, df: pd.DataFrame, **kwargs) -> Optional[Signal]:
        """Evaluate latest candle and generate Signal if conditions match."""
        pass
