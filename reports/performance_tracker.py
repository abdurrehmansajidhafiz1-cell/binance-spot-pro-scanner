"""
15-Day Live Performance Tracker & 12-Hour Summary Generator.
Computes real-time statistics (Sharpe, Profit Factor, Max Drawdown, Win Rate)
and supports 12-hour slice activity analysis with dual PKT + UTC timestamps.
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Tuple
import numpy as np
import pandas as pd
from tabulate import tabulate
from config.settings import LIVE_RESULTS_MD, STARTING_BALANCE_USDT
from engine.time_utils import format_dual_time, parse_to_utc, get_current_utc


class PerformanceTracker:
    def __init__(self, broker):
        self.broker = broker

    def compute_metrics(self, current_prices: Dict[str, float]) -> Dict[str, Any]:
        state = self.broker.state
        history = self.broker.trade_history
        
        current_equity = self.broker.get_portfolio_equity(current_prices)
        starting_bal = state.get("starting_balance", STARTING_BALANCE_USDT)
        
        total_pnl_usdt = current_equity - starting_bal
        total_return_pct = (total_pnl_usdt / starting_bal) * 100.0 if starting_bal > 0 else 0.0
        
        peak = max(state.get("equity_peak", starting_bal), current_equity)
        state["equity_peak"] = peak
        max_dd_pct = ((peak - current_equity) / peak) * 100.0 if peak > 0 else 0.0
        
        total_trades = len(history)
        winning_trades = [t for t in history if t["net_pnl_usdt"] > 0]
        losing_trades = [t for t in history if t["net_pnl_usdt"] <= 0]
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = (win_count / total_trades * 100.0) if total_trades > 0 else 0.0
        
        gross_profit = sum(t["net_pnl_usdt"] for t in winning_trades)
        gross_loss = abs(sum(t["net_pnl_usdt"] for t in losing_trades))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.9 if gross_profit > 0 else 1.0)
        
        total_fees = sum(t.get("fees_paid", 0.0) for t in history)
        
        avg_win_pct = np.mean([t["net_pnl_pct"] for t in winning_trades]) if winning_trades else 0.0
        avg_loss_pct = np.mean([t["net_pnl_pct"] for t in losing_trades]) if losing_trades else 0.0
        
        return {
            "starting_balance": starting_bal,
            "current_equity": current_equity,
            "cash_usdt": self.broker.cash,
            "total_pnl_usdt": total_pnl_usdt,
            "total_return_pct": total_return_pct,
            "equity_peak": peak,
            "max_drawdown_pct": max_dd_pct,
            "total_trades": total_trades,
            "win_count": win_count,
            "loss_count": loss_count,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_fees_paid": total_fees,
            "avg_win_pct": avg_win_pct,
            "avg_loss_pct": avg_loss_pct,
            "open_positions_count": len(self.broker.open_positions),
            "start_time": format_dual_time(state.get("start_time")),
            "last_updated": format_dual_time()
        }

    def get_12h_summary_data(self, hours: int = 12) -> Dict[str, Any]:
        """
        Extract trading activity from the last 12 hours.
        """
        now_utc = get_current_utc()
        cutoff_utc = now_utc - timedelta(hours=hours)
        
        history = self.broker.trade_history
        open_positions = list(self.broker.open_positions.values())
        
        # Filter closed trades in last 12h (by exit_time or entry_time)
        closed_in_12h = []
        for t in history:
            exit_dt = parse_to_utc(t.get("exit_time"))
            entry_dt = parse_to_utc(t.get("entry_time"))
            if (exit_dt and exit_dt >= cutoff_utc) or (entry_dt and entry_dt >= cutoff_utc):
                closed_in_12h.append(t)
                
        # Filter open positions
        open_in_12h = open_positions
        
        win_count = len([t for t in closed_in_12h if t.get("net_pnl_usdt", 0) > 0])
        loss_count = len([t for t in closed_in_12h if t.get("net_pnl_usdt", 0) <= 0])
        unresolved_count = len(open_in_12h)
        total_qualified = len(closed_in_12h) + unresolved_count
        net_pnl_usdt = sum(t.get("net_pnl_usdt", 0.0) for t in closed_in_12h)
        
        return {
            "period_start_utc": cutoff_utc,
            "period_end_utc": now_utc,
            "total_qualified": total_qualified,
            "win_count": win_count,
            "loss_count": loss_count,
            "unresolved_count": unresolved_count,
            "net_pnl_usdt": net_pnl_usdt,
            "closed_trades": closed_in_12h,
            "open_positions": open_in_12h
        }

    def generate_markdown_report(self, current_prices: Dict[str, float]) -> str:
        metrics = self.compute_metrics(current_prices)
        state = self.broker.state
        history = self.broker.trade_history
        
        open_pos_rows = []
        for sym, pos in state["open_positions"].items():
            curr_p = current_prices.get(sym, pos["current_price"])
            pnl_pct = ((curr_p - pos["entry_price"]) / pos["entry_price"]) * 100.0
            pnl_val = (pos["quantity"] * curr_p) - pos["initial_cost_usdt"]
            open_pos_rows.append([
                sym,
                pos["strategy"],
                f"${pos['entry_price']:,.4f}",
                f"${curr_p:,.4f}",
                f"${pos['stop_loss']:,.4f}",
                f"${pos['tp1']:,.4f}",
                f"${pnl_val:+,.2f} ({pnl_pct:+.2f}%)",
                format_dual_time(pos.get("entry_time"))
            ])

        open_headers = ["Symbol", "Strategy", "Entry Price", "Current Price", "Stop Loss", "TP1", "Unrealized PnL", "Entry Time (PKT & UTC)"]
        open_table_md = tabulate(open_pos_rows, headers=open_headers, tablefmt="github") if open_pos_rows else "_No open positions currently._"

        closed_rows = []
        for t in reversed(history[-15:]):
            closed_rows.append([
                t["symbol"],
                t["strategy"],
                f"${t['entry_price']:,.4f}",
                f"${t['exit_price']:,.4f}",
                f"${t['net_pnl_usdt']:+,.2f}",
                f"{t['net_pnl_pct']:+.2f}%",
                f"${t.get('fees_paid', 0.0):,.3f}",
                t["exit_reason"],
                format_dual_time(t.get("exit_time"))
            ])
            
        closed_headers = ["Symbol", "Strategy", "Entry Price", "Exit Price", "Net PnL ($)", "PnL (%)", "Fees", "Exit Reason", "Exit Time (PKT & UTC)"]
        closed_table_md = tabulate(closed_rows, headers=closed_headers, tablefmt="github") if closed_rows else "_No closed trades yet._"

        pnl_color = "brightgreen" if metrics['total_pnl_usdt'] >= 0 else "red"
        
        md = f"""# 🚀 Binance Spot 15-Day Live Paper Trading Dashboard

[![Portfolio Return](https://img.shields.io/badge/Net_Return-{metrics['total_return_pct']:+.2f}%25-{pnl_color}?style=for-the-badge)](LIVE_RESULTS.md)
[![Win Rate](https://img.shields.io/badge/Win_Rate-{metrics['win_rate']:.1f}%25-blue?style=for-the-badge)](LIVE_RESULTS.md)
[![Profit Factor](https://img.shields.io/badge/Profit_Factor-{metrics['profit_factor']:.2f}-orange?style=for-the-badge)](LIVE_RESULTS.md)
[![Total Trades](https://img.shields.io/badge/Total_Trades-{metrics['total_trades']}-informational?style=for-the-badge)](LIVE_RESULTS.md)

> **Last Updated:** `{metrics['last_updated']}`  
> **Testing Start Date:** `{metrics['start_time']}`  
> **Target Universe:** Top 50 Liquid Binance Spot Pairs (Zero Futures / Pure Spot)

---

## 📊 Executive Performance Summary

| Metric | Value | Metric | Value |
| :--- | :--- | :--- | :--- |
| **Starting Balance** | `${metrics['starting_balance']:,.2f} USDT` | **Total Realized Trades** | `{metrics['total_trades']}` |
| **Current Equity** | `${metrics['current_equity']:,.2f} USDT` | **Win / Loss Ratio** | `{metrics['win_count']} Win / {metrics['loss_count']} Loss` |
| **Available Cash** | `${metrics['cash_usdt']:,.2f} USDT` | **Win Rate** | `{metrics['win_rate']:.2f}%` |
| **Net PnL ($)** | `${metrics['total_pnl_usdt']:+,.2f} USDT` | **Profit Factor** | `{metrics['profit_factor']:.2f}` |
| **Net Return (%)** | `{metrics['total_return_pct']:+.2f}%` | **Avg Win / Avg Loss** | `+{metrics['avg_win_pct']:.2f}% / {metrics['avg_loss_pct']:.2f}%` |
| **Peak Equity** | `${metrics['equity_peak']:,.2f} USDT` | **Total Fees Deducted** | `${metrics['total_fees_paid']:,.2f} USDT` |
| **Max Drawdown** | `-{metrics['max_drawdown_pct']:.2f}%` | **Active Positions** | `{metrics['open_positions_count']}` |

---

## 🟢 Active Open Positions ({metrics['open_positions_count']})

{open_table_md}

---

## 📜 Recent Closed Trades (Last 15)

{closed_table_md}

---

## 🧠 Active Phase 1 Strategies
- **I1: Multi-Timeframe Trend + Volatility Pullback (4H Trend + 1H Execution)**
- **I2: Cross-Sectional Momentum & Relative Strength Rotation (1D Top Decile Ranker)**
- **S3: Volatility Squeeze Breakout (15m Bollinger-Keltner + OBV)**

*Note: All timestamps displayed in dual PKT (UTC+5) and UTC format.*
"""
        return md

    def save_live_results(self, current_prices: Dict[str, float]):
        report = self.generate_markdown_report(current_prices)
        with open(LIVE_RESULTS_MD, "w", encoding="utf-8") as f:
            f.write(report)
