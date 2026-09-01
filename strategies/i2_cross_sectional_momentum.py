"""
Strategy I2: Cross-Sectional Momentum & Relative Strength Rotation.
Timeframe: 1D Ranking + 4H Rebalancing.
Ranks all 50 coins by 14-day Risk-Adjusted Momentum (Return / Volatility).
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from strategies.base_strategy import BaseStrategy, Signal
from engine.indicators import calculate_sma, calculate_atr


class CrossSectionalMomentumStrategy(BaseStrategy):
    def __init__(self, top_n: int = 5, lookback_days: int = 14, vol_days: int = 30):
        super().__init__(name="I2_CROSS_SECTIONAL_MOMENTUM", timeframe="1d")
        self.top_n = top_n
        self.lookback_days = lookback_days
        self.vol_days = vol_days

    def calculate_momentum_score(self, df_1d: pd.DataFrame) -> Optional[float]:
        """Calculate Risk-Adjusted Momentum: R_14d / Vol_30d."""
        if df_1d is None or len(df_1d) < (self.vol_days + 5):
            return None
            
        close = df_1d['close']
        # 14-day cumulative return
        return_14d = (close.iloc[-1] / close.iloc[-self.lookback_days]) - 1.0
        
        # 30-day daily return volatility
        daily_returns = close.pct_change()
        vol_30d = daily_returns.iloc[-self.vol_days:].std()
        
        if vol_30d is None or vol_30d <= 0 or np.isnan(vol_30d):
            return None
            
        score = return_14d / vol_30d
        return float(score)

    def evaluate_universe(self, universe_data_1d: Dict[str, pd.DataFrame],
                          btc_df_1d: pd.DataFrame) -> Tuple[List[str], Dict[str, float], bool]:
        """
        Evaluate full 50-coin universe.
        Returns:
          - top_coins: List of top N symbols
          - scores: Dict of symbol -> score
          - btc_regime_bullish: Boolean
        """
        # 1. BTC Macro Filter (50-day SMA)
        if btc_df_1d is None or len(btc_df_1d) < 55:
            btc_bullish = True
        else:
            btc_sma_50 = calculate_sma(btc_df_1d['close'], 50).iloc[-1]
            btc_bullish = btc_df_1d['close'].iloc[-1] > btc_sma_50

        if not btc_bullish:
            return [], {}, False

        scores = {}
        for symbol, df_1d in universe_data_1d.items():
            if symbol == "BTCUSDT":
                continue
            score = self.calculate_momentum_score(df_1d)
            if score is not None and score > 0: # Only positive momentum
                scores[symbol] = score

        # Rank descending
        sorted_coins = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_coins = [symbol for symbol, _ in sorted_coins[:self.top_n]]
        
        return top_coins, scores, True

    def evaluate(self, symbol: str, df: pd.DataFrame, **kwargs) -> Optional[Signal]:
        # Handled at universe level via evaluate_universe
        return None
