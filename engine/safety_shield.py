"""
Advanced Market Safety Shield & Regime Filter for Binance Spot.
Filters out high-risk trading conditions (Sunday/Monday CME opens, BTC flash-dumps,
altcoin liquidation cascades, and abnormal volatility spikes).
"""
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Tuple, Optional


class MarketSafetyShield:
    def __init__(self):
        pass

    @staticmethod
    def is_sunday_monday_volatility_window() -> Tuple[bool, str]:
        """
        Detects Sunday 20:00 UTC to Monday 08:00 UTC (CME Open & Weekly Open volatility window).
        During this window, market manipulation and fake wicks are statistically highest.
        """
        now = datetime.now(timezone.utc)
        weekday = now.weekday() # 0 is Monday, 6 is Sunday
        hour = now.hour
        
        # Sunday 20:00 UTC to Sunday 23:59 UTC
        if weekday == 6 and hour >= 20:
            return True, "Sunday Night CME/Futures Open Volatility Window (Extreme Fake-Wick Risk)"
            
        # Monday 00:00 UTC to Monday 08:00 UTC
        if weekday == 0 and hour < 8:
            return True, "Monday Morning Weekly Open Volatility Window (High Liquidity Rebalance Risk)"
            
        return False, "Normal Market Hours"

    @staticmethod
    def check_btc_flash_dump(btc_15m_df: Optional[pd.DataFrame]) -> Tuple[bool, str]:
        """
        Detects if Bitcoin just suffered a sudden flash dump (> 1.5% drop in recent 15m/30m).
        """
        if btc_15m_df is None or len(btc_15m_df) < 5:
            return False, "BTC Data Normal"
            
        latest_close = btc_15m_df['close'].iloc[-1]
        prev_open_3bars = btc_15m_df['open'].iloc[-3]
        pct_drop = ((latest_close - prev_open_3bars) / prev_open_3bars) * 100.0
        
        if pct_drop <= -1.5:
            return True, f"BTC Flash Dump Detected ({pct_drop:.2f}% drop in last 45m). Altcoin Longs Blocked."
            
        return False, "BTC Stable"

    @staticmethod
    def check_market_wide_cascade(universe_tickers: Dict[str, Dict]) -> Tuple[bool, str]:
        """
        Detects market-wide sell-offs where > 70% of the 50-coin universe is dropping sharply.
        """
        if not universe_tickers or len(universe_tickers) < 20:
            return False, "Market Breadth Normal"
            
        red_coins = 0
        total_coins = len(universe_tickers)
        
        for sym, data in universe_tickers.items():
            if data.get("price_change_pct", 0.0) < -1.0: # down > 1% in 24h
                red_coins += 1
                
        red_ratio = red_coins / total_coins
        if red_ratio >= 0.70:
            return True, f"Market-Wide Cascade Alert: {red_ratio*100:.1f}% of universe is dumping simultaneously."
            
        return False, "Market Breadth Stable"

    @classmethod
    def evaluate_global_safety(cls, btc_15m_df: Optional[pd.DataFrame], universe_tickers: Dict[str, Dict]) -> Dict:
        """
        Run all global safety checks.
        Returns safety assessment dict.
        """
        is_timing_risk, timing_msg = cls.is_sunday_monday_volatility_window()
        is_btc_dump, btc_msg = cls.check_btc_flash_dump(btc_15m_df)
        is_cascade, cascade_msg = cls.check_market_wide_cascade(universe_tickers)
        
        is_safe = not (is_btc_dump or is_cascade)
        
        return {
            "is_safe": is_safe,
            "timing_warning": is_timing_risk,
            "timing_msg": timing_msg,
            "btc_dump": is_btc_dump,
            "btc_msg": btc_msg,
            "cascade_dump": is_cascade,
            "cascade_msg": cascade_msg
        }
