"""
Strategy I1: Multi-Timeframe Trend + Volatility-Adjusted Pullback.
Timeframes: 4H (Macro Trend Filter) + 1H (Pullback & Execution).
"""
import pandas as pd
from typing import Optional
from strategies.base_strategy import BaseStrategy, Signal
from engine.indicators import (
    calculate_ema, calculate_supertrend, calculate_rsi, calculate_atr
)


class MultiTimeframePullbackStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(name="I1_MTF_TREND_PULLBACK", timeframe="1h")

    def evaluate(self, symbol: str, df: pd.DataFrame, df_4h: Optional[pd.DataFrame] = None, **kwargs) -> Optional[Signal]:
        """
        df: 1H execution dataframe.
        df_4h: 4H macro trend dataframe.
        """
        if df is None or len(df) < 60:
            return None
        if df_4h is None or len(df_4h) < 60:
            return None

        # 1. Macro 4H Trend Verification
        ema_200_4h = calculate_ema(df_4h['close'], 200)
        supertrend_4h, direction_4h = calculate_supertrend(df_4h, period=10, multiplier=3.0)
        
        curr_4h_idx = len(df_4h) - 1
        is_4h_bullish = (
            df_4h['close'].iloc[curr_4h_idx] > ema_200_4h.iloc[curr_4h_idx] and
            direction_4h.iloc[curr_4h_idx] == 1
        )
        
        if not is_4h_bullish:
            return None

        # 2. 1H Execution Pullback Verification
        ema_8_1h = calculate_ema(df['close'], 8)
        ema_21_1h = calculate_ema(df['close'], 21)
        ema_50_1h = calculate_ema(df['close'], 50)
        rsi_1h = calculate_rsi(df['close'], 14)
        atr_1h = calculate_atr(df, 14)
        
        curr_idx = len(df) - 1
        prev_idx = curr_idx - 1
        
        # Pullback check: Recent low dipped into EMA21 zone without violating EMA50
        recent_low_min = df['low'].iloc[curr_idx-3:curr_idx+1].min()
        dipped_into_ema21 = recent_low_min <= (ema_21_1h.iloc[curr_idx] * 1.004)
        above_ema50 = recent_low_min >= (ema_50_1h.iloc[curr_idx] * 0.995)
        
        # RSI Oscillator reset in cooling zone (38 - 54)
        rsi_cooled = 38.0 <= rsi_1h.iloc[prev_idx] <= 55.0 or 38.0 <= rsi_1h.iloc[curr_idx] <= 55.0
        
        # Trigger Candle: 1H Green Candle closes back above EMA 8
        is_green_reversal = (
            df['close'].iloc[curr_idx] > df['open'].iloc[curr_idx] and
            df['close'].iloc[curr_idx] > ema_8_1h.iloc[curr_idx]
        )
        
        # Volume confirmation
        vol_sma_1h = df['volume'].rolling(20).mean().iloc[curr_idx]
        vol_confirmed = df['volume'].iloc[curr_idx] >= (vol_sma_1h * 0.9)

        if dipped_into_ema21 and above_ema50 and rsi_cooled and is_green_reversal and vol_confirmed:
            curr_price = df['close'].iloc[curr_idx]
            curr_atr = atr_1h.iloc[curr_idx]
            swing_low = df['low'].iloc[curr_idx-5:curr_idx+1].min()
            
            # Stop Loss: Swing Low - 0.3 * ATR
            sl_price = min(swing_low - (0.3 * curr_atr), ema_50_1h.iloc[curr_idx] - (0.5 * curr_atr))
            risk_distance = curr_price - sl_price
            
            if risk_distance <= 0:
                return None
                
            # TP1: 1.5R (~2.5% - 4.0%)
            tp1_price = curr_price + (1.5 * risk_distance)
            # TP2: 3.0R (~5.0% - 8.0%)
            tp2_price = curr_price + (3.0 * risk_distance)
            
            return Signal(
                symbol=symbol,
                action="BUY",
                price=curr_price,
                stop_loss=round(sl_price, 6),
                tp1=round(tp1_price, 6),
                tp2=round(tp2_price, 6),
                strategy_name=self.name,
                reason="4H Macro Trend confirmed + 1H EMA21 Pullback Reversal with RSI Reset",
                metadata={
                    "risk_distance_pct": round((risk_distance / curr_price) * 100, 2),
                    "rsi_1h": round(float(rsi_1h.iloc[curr_idx]), 2),
                    "supertrend_4h": "BULLISH"
                }
            )

        return None
