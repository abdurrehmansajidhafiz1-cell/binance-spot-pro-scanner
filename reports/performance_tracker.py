"""
15-Day Live Performance Tracker & Postmortem Dashboard Generator.
Accurately tracks unique trade entities, milestones (TP1, TP2, SL),
and formats complete trade postmortems with dual PKT + UTC timestamps.
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
import numpy as np
from tabulate import tabulate
from config.settings import LIVE_RESULTS_MD, STARTING_BALANCE_USDT, PKR_PER_USD, REFERENCE_BUDGET_USDT, TRADE_BUDGET_USDT
from engine.time_utils import format_dual_time, parse_to_utc, get_current_utc


class PerformanceTracker:
    def __init__(self, broker):
        self.broker = broker

    def compute_metrics(self, current_prices: Dict[str, float]) -> Dict[str, Any]:
        state = self.broker.state
        history = self.broker.trade_history
        open_positions = self.broker.open_positions
        
        current_equity = self.broker.get_portfolio_equity(current_prices)
        starting_bal = state.get("starting_balance", STARTING_BALANCE_USDT)
        
        total_pnl_usdt = current_equity - starting_bal
        total_return_pct = (total_pnl_usdt / starting_bal) * 100.0 if starting_bal > 0 else 0.0
        
        peak = max(state.get("equity_peak", starting_bal), current_equity)
        state["equity_peak"] = peak
        max_dd_pct = ((peak - current_equity) / peak) * 100.0 if peak > 0 else 0.0
        
        completed_trades_count = len(history)
        active_trades_count = len(open_positions)
        total_qualified_trades = completed_trades_count + active_trades_count
        
        winning_trades = [t for t in history if t.get("net_pnl_usdt", 0) > 0]
        losing_trades = [t for t in history if t.get("net_pnl_usdt", 0) < 0]
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = (win_count / completed_trades_count * 100.0) if completed_trades_count > 0 else 0.0
        
        gross_profit = sum(t.get("net_pnl_usdt", 0) for t in winning_trades)
        gross_loss = abs(sum(t.get("net_pnl_usdt", 0) for t in losing_trades))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.9 if gross_profit > 0 else 1.0)
        
        total_fees = sum(t.get("fees_paid", 0.0) for t in history) + sum(p.get("fees_paid", 0.0) for p in open_positions.values())
        
        avg_win_pct = np.mean([t.get("net_pnl_pct", 0) for t in winning_trades]) if winning_trades else 0.0
        avg_loss_pct = np.mean([t.get("net_pnl_pct", 0) for t in losing_trades]) if losing_trades else 0.0
        
        return {
            "starting_balance": starting_bal,
            "current_equity": current_equity,
            "cash_usdt": self.broker.cash,
            "total_pnl_usdt": total_pnl_usdt,
            "total_return_pct": total_return_pct,
            "equity_peak": peak,
            "max_drawdown_pct": max_dd_pct,
            "total_qualified_trades": total_qualified_trades,
            "completed_trades_count": completed_trades_count,
            "active_trades_count": active_trades_count,
            "win_count": win_count,
            "loss_count": loss_count,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_fees_paid": total_fees,
            "avg_win_pct": avg_win_pct,
            "avg_loss_pct": avg_loss_pct,
            "start_time": format_dual_time(state.get("start_time")),
            "last_updated": format_dual_time()
        }

    def get_12h_summary_data(self, hours: int = 12) -> Dict[str, Any]:
        """
        Extract trading activity from the last 12 hours based on unique trades.
        """
        now_utc = get_current_utc()
        cutoff_utc = now_utc - timedelta(hours=hours)
        
        history = self.broker.trade_history
        open_positions = list(self.broker.open_positions.values())
        
        closed_in_12h = []
        for t in history:
            exit_dt = parse_to_utc(t.get("exit_time"))
            entry_dt = parse_to_utc(t.get("entry_time"))
            if (exit_dt and exit_dt >= cutoff_utc) or (entry_dt and entry_dt >= cutoff_utc):
                closed_in_12h.append(t)
                
        open_in_12h = open_positions
        
        win_count = len([t for t in closed_in_12h if t.get("net_pnl_usdt", 0) > 0])
        loss_count = len([t for t in closed_in_12h if t.get("net_pnl_usdt", 0) < 0])
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
        
        # 1. Format Active Positions with complete timeline and TradingView Timeframe
        open_pos_rows = []
        for sym, pos in state["open_positions"].items():
            curr_p = current_prices.get(sym, pos["current_price"])
            entry_p = pos["entry_price"]
            pnl_pct = ((curr_p - entry_p) / entry_p) * 100.0
            pnl_val = (pos.get("remaining_quantity", pos["quantity"]) * curr_p) - pos.get("remaining_cost_usdt", pos["initial_cost_usdt"]) + pos.get("realized_pnl_usdt", 0.0)
            
            tp1_status = f"${pos['tp1']:,.4f} " + ("(HIT)" if pos.get("tp1_reached") else "(Pending)")
            tp2_status = f"${pos['tp2']:,.4f} " + ("(HIT)" if pos.get("tp2_reached") else "(Pending)")
            tf_display = pos.get("timeframe", "15m" if "S3" in pos["strategy"] else "1h (4h Trend)")
            
            open_pos_rows.append([
                sym,
                pos["strategy"],
                f"<b>{tf_display}</b>",
                format_dual_time(pos.get("zone_candle_time")),
                format_dual_time(pos.get("signal_time")),
                f"${entry_p:,.4f}<br><small>{format_dual_time(pos.get('entry_time'))}</small>",
                f"${curr_p:,.4f}",
                f"${pos['stop_loss']:,.4f}",
                f"{tp1_status}<br>{tp2_status}",
                f"{pnl_val:+,.2f} ({pnl_pct:+.2f}%)",
                "🟡 ACTIVE"
            ])

        open_headers = [
            "Symbol", "Strategy", "TradingView Timeframe", "Zone Formed (PKT/UTC)", "Signal Time (PKT/UTC)",
            "Entry Price & Time (PKT/UTC)", "Current Price", "Stop Loss",
            "Targets (TP1 / TP2)", "Unrealized PnL", "Status"
        ]
        open_table_md = tabulate(open_pos_rows, headers=open_headers, tablefmt="github") if open_pos_rows else "_No active open positions currently._"

        # 2. Format Completed Trades Postmortem History with PKR calculations
        closed_rows = []
        for t in reversed(history):
            pnl_val   = t.get("net_pnl_usdt", 0.0)
            pnl_pct   = t.get("net_pnl_pct", 0.0)
            fees_usd  = t.get("fees_paid", 0.0)
            result_badge = "🟢 FULL WIN" if "TP2" in t.get("exit_reason", "") else ("🟢 PARTIAL WIN" if pnl_val > 0 else "🔴 LOSS")
            tf_display = t.get("timeframe", "15m" if "S3" in t["strategy"] else "1h")
            
            tp1_hit_str = format_dual_time(t.get("tp1_hit_time")) if t.get("tp1_hit_time") else "-"
            tp2_hit_str = format_dual_time(t.get("tp2_hit_time")) if t.get("tp2_hit_time") else "-"
            sl_hit_str  = format_dual_time(t.get("sl_hit_time")) if t.get("sl_hit_time") else "-"
            
            # PKR Calculations
            # $100 actual trade
            pnl_100_pkr   = pnl_val * PKR_PER_USD
            fees_100_pkr  = fees_usd * PKR_PER_USD
            # $35 reference-only calculation (scale proportionally from $100)
            ratio_35      = REFERENCE_BUDGET_USDT / TRADE_BUDGET_USDT   # 35/100 = 0.35
            pnl_35_pkr    = pnl_val  * ratio_35 * PKR_PER_USD
            fees_35_pkr   = fees_usd * ratio_35 * PKR_PER_USD
            pnl_35_sign   = "+" if pnl_35_pkr >= 0 else ""

            pkr_block = (
                f"💵 **$100 Trade:** `{'+' if pnl_100_pkr >= 0 else ''}{pnl_100_pkr:,.0f} PKR` profit"
                f" | Fees: `{fees_100_pkr:,.0f} PKR`<br>"
                f"📌 **$35 Ref:** `{pnl_35_sign}{pnl_35_pkr:,.0f} PKR` profit"
                f" | Fees: `{fees_35_pkr:,.0f} PKR`"
            )
            
            closed_rows.append([
                t["symbol"],
                t["strategy"],
                f"**{tf_display}**",
                format_dual_time(t.get("zone_candle_time")),
                format_dual_time(t.get("signal_time")),
                f"${t['entry_price']:,.4f}<br><small>{format_dual_time(t.get('entry_time'))}</small>",
                f"${t.get('tp1', 0):,.4f}<br><small>{tp1_hit_str}</small>",
                f"${t.get('tp2', 0):,.4f}<br><small>{tp2_hit_str}</small>",
                sl_hit_str,
                f"{pnl_val:+,.2f} ({pnl_pct:+.2f}%)",
                pkr_block,
                result_badge
            ])
            
        closed_headers = [
            "Symbol", "Strategy", "TradingView Timeframe", "Zone Formed (PKT/UTC)", "Signal Time (PKT/UTC)",
            "Entry Price & Time", "TP1 Price & Hit Time", "TP2 Price & Hit Time",
            "SL Hit Time", "Net PnL ($ / %)", f"PKR Calculations (Rate: ₨{PKR_PER_USD:.0f}/$)", "Final Result"
        ]
        closed_table_md = tabulate(closed_rows, headers=closed_headers, tablefmt="github") if closed_rows else "_No closed trades yet._"

        pnl_color = "brightgreen" if metrics['total_pnl_usdt'] >= 0 else "red"
        
        md = f"""# 🚀 Binance Spot 15-Day Live Paper Trading Dashboard

[![Portfolio Return](https://img.shields.io/badge/Net_Return-{metrics['total_return_pct']:+.2f}%25-{pnl_color}?style=for-the-badge)](LIVE_RESULTS.md)
[![Win Rate](https://img.shields.io/badge/Win_Rate-{metrics['win_rate']:.1f}%25-blue?style=for-the-badge)](LIVE_RESULTS.md)
[![Profit Factor](https://img.shields.io/badge/Profit_Factor-{metrics['profit_factor']:.2f}-orange?style=for-the-badge)](LIVE_RESULTS.md)
[![Total Qualified Trades](https://img.shields.io/badge/Total_Qualified-{metrics['total_qualified_trades']}-informational?style=for-the-badge)](LIVE_RESULTS.md)

> **Last Updated:** `{metrics['last_updated']}`  
> **Testing Start Date:** `{metrics['start_time']}`  
> **Target Universe:** Top 50 Liquid Binance Spot Pairs (Zero Futures / Pure Spot)
> **Fixed Trade Budget:** `$100 USDT per trade` | **PKR Rate:** `₨{PKR_PER_USD:.0f} per $1 USD`

---

## 📊 Executive Performance Summary (Unique Trades)

| Metric | Value | Metric | Value |
| :--- | :--- | :--- | :--- |
| **Starting Balance** | `${metrics['starting_balance']:,.2f} USDT` | **Total Qualified Trades** | `{metrics['total_qualified_trades']} Unique Trades` |
| **Current Equity** | `${metrics['current_equity']:,.2f} USDT` | **Completed Trades** | `{metrics['completed_trades_count']} Trades` |
| **Available Cash** | `${metrics['cash_usdt']:,.2f} USDT` | **Active / In-Trade** | `{metrics['active_trades_count']} Trade` |
| **Net PnL ($)** | `${metrics['total_pnl_usdt']:+,.2f} USDT` | **Win / Loss Ratio** | `{metrics['win_count']} Win / {metrics['loss_count']} Loss` |
| **Net Return (%)** | `{metrics['total_return_pct']:+.2f}%` | **Win Rate** | `{metrics['win_rate']:.2f}%` |
| **Peak Equity** | `${metrics['equity_peak']:,.2f} USDT` | **Profit Factor** | `{metrics['profit_factor']:.2f}` |
| **Max Drawdown** | `-{metrics['max_drawdown_pct']:.2f}%` | **Total Fees Deducted** | `${metrics['total_fees_paid']:,.2f} USDT` |

---

## 🟡 Active Open Positions ({metrics['active_trades_count']})

{open_table_md}

---

## 📜 Completed Trades Postmortem History ({metrics['completed_trades_count']})

> **PKR Column Guide:**
> - 💵 `$100 Trade` → Actual realized profit/fees in PKR (actual budget used)
> - 📌 `$35 Ref` → Reference-only: what the same trade would have earned with $35 budget (no actual trades at $35)
> - PKR Rate used: **₨{PKR_PER_USD:.0f} per $1 USD**

{closed_table_md}

---

## 🧠 Active Phase 1 Strategies
- **I1: Multi-Timeframe Trend + Volatility Pullback (4H Trend + 1H Execution)**
- **I2: Cross-Sectional Momentum & Relative Strength Rotation (1D Top Decile Ranker)**
- **S3: Volatility Squeeze Breakout (15m Bollinger-Keltner + OBV)**

*Note: All milestones (Zone Formation, Signal Generation, Entry, TP1, TP2, SL) are tracked with exact Pakistan Standard Time (PKT) and UTC timestamps. PKR calculations are for informational reference only.*
"""
        return md

    def save_live_results(self, current_prices: Dict[str, float]):
        report = self.generate_markdown_report(current_prices)
        with open(LIVE_RESULTS_MD, "w", encoding="utf-8") as f:
            f.write(report)
