"""
Strategy S3: Volatility Squeeze Breakout (Bollinger-Keltner + OBV).
Timeframe: 15m.
"""
import pandas as pd
from typing import Optional
from strategies.base_strategy import BaseStrategy, Signal
from engine.indicators import calculate_squeeze, calculate_obv, calculate_ema, calculate_atr


class VolatilitySqueezeStrategy(BaseStrategy):
    def __init__(self, bb_period: int = 20, bb_std: float = 2.0, kc_period: int = 20, kc_mult: float = 1.5):
        super().__init__(name="S3_VOLATILITY_SQUEEZE", timeframe="15m")
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.kc_period = kc_period
        self.kc_mult = kc_mult

    def evaluate(self, symbol: str, df: pd.DataFrame, **kwargs) -> Optional[Signal]:
        if df is None or len(df) < 50:
            return None

        # Calculate Squeeze & Channels
        is_squeeze, bb_upper, bb_mid, bb_lower, kc_upper, kc_mid, kc_lower, mom_hist = calculate_squeeze(
            df, self.bb_period, self.bb_std, self.kc_period, self.kc_mult
        )
        
        # Calculate OBV & OBV EMA
        obv = calculate_obv(df)
        obv_ema = calculate_ema(obv, 20)
        atr = calculate_atr(df, 14)
        
        # We check the completed candle (index -2) and latest candle (index -1)
        curr_idx = len(df) - 1
        prev_idx = curr_idx - 1
        
        # Condition 1: Squeeze was active in previous 2 to 6 bars
        recent_squeeze = is_squeeze.iloc[prev_idx-4:prev_idx].any()
        
        # Condition 2: Squeeze Fires (Current BB upper is above KC upper OR Squeeze just turned False)
        squeeze_fired = not is_squeeze.iloc[curr_idx] and is_squeeze.iloc[prev_idx]
        is_breakout_band = df['close'].iloc[curr_idx] > bb_upper.iloc[curr_idx]
        
        # Condition 3: Momentum is positive and expanding
        mom_positive = mom_hist.iloc[curr_idx] > 0 and mom_hist.iloc[curr_idx] > mom_hist.iloc[prev_idx]
        
        # Condition 4: OBV is above its EMA
        obv_bullish = obv.iloc[curr_idx] > obv_ema.iloc[curr_idx]
        
        # Condition 5: Volume confirmation (Current volume > 1.2 * SMA volume)
        vol_sma = df['volume'].rolling(20).mean().iloc[curr_idx]
        vol_confirmed = df['volume'].iloc[curr_idx] > (vol_sma * 1.2)

        if (recent_squeeze or squeeze_fired) and is_breakout_band and mom_positive and obv_bullish and vol_confirmed:
            curr_price = df['close'].iloc[curr_idx]
            curr_atr = atr.iloc[curr_idx]
            
            # Stop Loss: Keltner Midline - 0.5 * ATR
            sl_price = max(kc_mid.iloc[curr_idx] - (0.5 * curr_atr), curr_price * 0.975) # max 2.5% risk
            
            # TP1: +1.0% quick fee lock / mean target
            tp1_price = curr_price * 1.010
            
            # TP2: +2.0 * ATR full volatility expansion
            tp2_price = curr_price + (2.0 * curr_atr)
            
            return Signal(
                symbol=symbol,
                action="BUY",
                price=curr_price,
                stop_loss=round(sl_price, 6),
                tp1=round(tp1_price, 6),
                tp2=round(tp2_price, 6),
                strategy_name=self.name,
                reason="Squeeze Expansion Breakout above Upper BB with OBV + Volume Confirmation",
                metadata={
                    "atr": round(curr_atr, 6),
                    "mom_hist": round(float(mom_hist.iloc[curr_idx]), 4),
                    "bb_upper": round(float(bb_upper.iloc[curr_idx]), 6)
                }
            )

        return None
