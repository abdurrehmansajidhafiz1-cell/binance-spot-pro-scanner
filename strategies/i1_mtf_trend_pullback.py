"""
Strategy I1: Multi-Timeframe Trend + Volatility-Adjusted Pullback.
Timeframes: 4H (Macro Trend Filter) + 1H (Pullback & Execution).

Filters added (post Day-1 to Day-8 forensic loss investigation):
  F1 — Max Stop-Loss Hard Cap: SL distance must be <= 3.5% of entry price.
  F2 — BTC 1H EMA20 Health Gate: Reject altcoin longs when BTC 1H < EMA20.
  F3 — 15M Reversal Candle Confirmation: Require bullish 15M close above prev high.
  F4 — Weak Coin Volume + Cooldown: Applied in main.py before calling evaluate().
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
        df: 1H execution dataframe (closed candles only).
        df_4h: 4H macro trend dataframe (closed candles only).

        Optional kwargs:
          df_btc_1h (pd.DataFrame): BTC USDT 1H closed candles — used for Filter 2.
          df_15m    (pd.DataFrame): Symbol 15M closed candles  — used for Filter 3.
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

        # ── FILTER 2: BTC 1H EMA20 Macro Health Gate ──────────────────────────
        # If BTC 1H close is below its own 20-period EMA, altcoin longs are
        # dangerous. Reject the signal to avoid market-wide dump casualties.
        # Root-cause: Day-5 — ICP, ALGO & SOL all stopped out in the SAME 1-min
        # candle when BTC flushed. BTC was already below its 1H EMA20 at entry.
        df_btc_1h: Optional[pd.DataFrame] = kwargs.get("df_btc_1h")
        if df_btc_1h is not None and len(df_btc_1h) >= 25:
            btc_ema20 = calculate_ema(df_btc_1h['close'], 20)
            btc_curr_idx = len(df_btc_1h) - 1
            if df_btc_1h['close'].iloc[btc_curr_idx] < btc_ema20.iloc[btc_curr_idx]:
                return None  # BTC bearish on 1H — skip all altcoin I1 longs

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

        # ── FILTER 3: 15M Reversal Candle Confirmation (Anti-Falling-Knife) ───
        # Require at least 1 closed 15M bullish candle whose close is ABOVE the
        # prior 15M candle's high. This confirms buyers are genuinely stepping in,
        # not just a 1H zone touch with continued selling pressure.
        # Root-cause: 7 of 11 losses had highest_price == entry_price (zero bounce).
        df_15m: Optional[pd.DataFrame] = kwargs.get("df_15m")
        reversal_15m_confirmed = False
        if df_15m is not None and len(df_15m) >= 4:
            m15_curr = len(df_15m) - 1
            m15_prev = m15_curr - 1
            m15_2ago = m15_curr - 2
            is_15m_green = df_15m['close'].iloc[m15_curr] > df_15m['open'].iloc[m15_curr]
            closes_above_prev_high = df_15m['close'].iloc[m15_curr] > df_15m['high'].iloc[m15_prev]
            # Also accept if the previous 15M candle already showed the breakout
            prev_15m_green = df_15m['close'].iloc[m15_prev] > df_15m['open'].iloc[m15_prev]
            prev_closes_above_2ago_high = df_15m['close'].iloc[m15_prev] > df_15m['high'].iloc[m15_2ago]
            reversal_15m_confirmed = (
                (is_15m_green and closes_above_prev_high) or
                (prev_15m_green and prev_closes_above_2ago_high)
            )
        else:
            # If 15M data not provided, fall back gracefully (backward-compatible)
            reversal_15m_confirmed = True

        if dipped_into_ema21 and above_ema50 and rsi_cooled and is_green_reversal and vol_confirmed and reversal_15m_confirmed:
            curr_price = df['close'].iloc[curr_idx]
            curr_atr = atr_1h.iloc[curr_idx]
            swing_low = df['low'].iloc[curr_idx-5:curr_idx+1].min()
            
            # Stop Loss: Swing Low - 0.3 * ATR
            sl_price = min(swing_low - (0.3 * curr_atr), ema_50_1h.iloc[curr_idx] - (0.5 * curr_atr))
            risk_distance = curr_price - sl_price
            
            if risk_distance <= 0:
                return None

            # ── FILTER 1: Maximum Stop-Loss Hard Cap (≤ 3.5%) ────────────────
            # If SL is wider than 3.5%, coin needs 5-10% pump to hit TP1 —
            # statistically unfavorable in choppy/neutral markets.
            # Root-cause: EGLD (8.0% SL) and FIL (4.5% SL) caused the two
            # single largest losses in the entire 8-day audit period.
            risk_distance_pct = (risk_distance / curr_price) * 100
            if risk_distance_pct > 3.5:
                return None  # SL too wide — disqualify this signal
                
            # TP1: 1.5R (~2.5% - 4.0%)
            tp1_price = curr_price + (1.5 * risk_distance)
            # TP2: 3.0R (~5.0% - 8.0%)
            tp2_price = curr_price + (3.0 * risk_distance)
            
            # Dynamic decimal precision for micro-penny tokens
            dec_places = 8 if curr_price < 0.01 else (6 if curr_price < 1.0 else 4)
            
            return Signal(
                symbol=symbol,
                action="BUY",
                price=curr_price,
                stop_loss=round(sl_price, dec_places),
                tp1=round(tp1_price, dec_places),
                tp2=round(tp2_price, dec_places),
                strategy_name=self.name,
                reason="4H Trend OK + 1H EMA21 Pullback + RSI Reset + 15M Reversal Confirmed + BTC Health OK + SL <= 3.5%",
                metadata={
                    "risk_distance_pct": round(risk_distance_pct, 2),
                    "rsi_1h": round(float(rsi_1h.iloc[curr_idx]), 2),
                    "supertrend_4h": "BULLISH"
                }
            )

        return None
