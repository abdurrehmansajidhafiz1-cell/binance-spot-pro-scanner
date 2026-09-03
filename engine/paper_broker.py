"""
Realistic Binance Spot Virtual Paper Broker.
Models maker/taker fees, bid-ask spread, slippage, and unified trade lifecycle.
Each trade is a single entity from entry to final exit (milestones like TP1 are tracked within the trade).
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple, Any, List
from config.settings import (
    SPOT_FEE_RATE, SLIPPAGE_RATE, MAX_CONCURRENT_POSITIONS,
    STARTING_BALANCE_USDT, TRADE_BUDGET_USDT
)
from engine.state_manager import StateManager
from engine.time_utils import get_current_utc, format_dual_time


class PaperBroker:
    def __init__(self, state_manager: Optional[StateManager] = None):
        self.state_manager = state_manager or StateManager()
        self.state = self.state_manager.load_state()
        self.trade_history = self.state_manager.load_trade_history()
        
        if not self.state.get("start_time"):
            self.state["start_time"] = get_current_utc().isoformat()
            self.save()

    @property
    def cash(self) -> float:
        return self.state["cash_usdt"]

    @property
    def open_positions(self) -> Dict[str, Any]:
        return self.state["open_positions"]

    def get_portfolio_equity(self, current_prices: Dict[str, float]) -> float:
        """Calculate total account equity = Cash + Current Market Value of Open Positions."""
        equity = self.cash
        for symbol, pos in self.open_positions.items():
            price = current_prices.get(symbol, pos["current_price"])
            equity += pos["remaining_quantity"] * price
        return equity

    def calculate_position_size(self, current_price: float, stop_loss: float, total_equity: float) -> Tuple[float, float]:
        """
        Fixed $100 USDT allocation per trade.
        Every trade — regardless of portfolio size — uses exactly $100 USDT.
        Profit/Loss is always reported relative to the $100 base investment.
        """
        # Ensure we have enough cash (at least TRADE_BUDGET_USDT + fees)
        available = min(TRADE_BUDGET_USDT, self.cash * 0.98)
        position_cost_usdt = available
        raw_quantity = position_cost_usdt / current_price

        return raw_quantity, position_cost_usdt

    def can_open_position(self, symbol: str) -> bool:
        """Check if portfolio capacity allows new trade."""
        if symbol in self.open_positions:
            return False
        if len(self.open_positions) >= MAX_CONCURRENT_POSITIONS:
            return False
        if self.cash < 101.0: # Minimum $101 cash threshold (covers $100 trade + fees)
            return False
        return True

    def open_long_position(self, symbol: str, strategy_name: str, current_price: float,
                           stop_loss: float, tp1: float, tp2: float,
                           timeframe: str = "15m",
                           zone_candle_time: Optional[str] = None,
                           metadata: Optional[Dict] = None) -> Optional[Dict]:
        """
        Execute Long Spot order with realistic slippage and fee deduction.
        Initializes a single Trade Entity.
        """
        if not self.can_open_position(symbol):
            return None

        # Apply slippage on entry (Buy higher than mid price)
        exec_price = current_price * (1.0 + SLIPPAGE_RATE)
        
        # Approximate equity for sizing
        equity = self.get_portfolio_equity({symbol: current_price})
        quantity, cost_usdt = self.calculate_position_size(exec_price, stop_loss, equity)
        
        if cost_usdt < 20.0 or quantity <= 0:
            return None
            
        fee_paid = cost_usdt * SPOT_FEE_RATE
        total_deduction = cost_usdt + fee_paid
        
        if total_deduction > self.cash:
            cost_usdt = (self.cash * 0.98) / (1.0 + SPOT_FEE_RATE)
            quantity = cost_usdt / exec_price
            fee_paid = cost_usdt * SPOT_FEE_RATE
            total_deduction = cost_usdt + fee_paid

        self.state["cash_usdt"] -= total_deduction
        now_iso = get_current_utc().isoformat()
        
        trade_id = f"T_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{symbol}"
        
        position = {
            "trade_id": trade_id,
            "symbol": symbol,
            "strategy": strategy_name,
            "timeframe": timeframe,
            "zone_candle_time": zone_candle_time or now_iso,
            "signal_time": now_iso,
            "entry_time": now_iso,
            "entry_price": exec_price,
            "current_price": exec_price,
            "initial_quantity": quantity,
            "remaining_quantity": quantity,
            "quantity": quantity, # backwards compatibility
            "initial_cost_usdt": cost_usdt,
            "remaining_cost_usdt": cost_usdt,
            "stop_loss": stop_loss,
            "initial_stop_loss": stop_loss,
            "tp1": tp1,
            "tp2": tp2,
            "tp1_reached": False,
            "tp1_hit_time": None,
            "tp1_exit_price": None,
            "tp2_reached": False,
            "tp2_hit_time": None,
            "tp2_exit_price": None,
            "sl_hit_time": None,
            "sl_exit_price": None,
            "exit_time": None,
            "exit_reason": None,
            "status": "ACTIVE",
            "highest_price": exec_price,
            "fees_paid": fee_paid,
            "realized_pnl_usdt": 0.0,
            "metadata": metadata or {}
        }
        
        self.state["open_positions"][symbol] = position
        self.save()
        return position

    def update_position_market_price(self, symbol: str, current_price: float, high_price: float, low_price: float) -> Optional[Dict]:
        """
        Check Stop Loss, TP1, TP2 triggers on new bar data.
        Returns trade event dict if a milestone or close occurred.
        """
        if symbol not in self.open_positions:
            return None
            
        pos = self.open_positions[symbol]
        pos["current_price"] = current_price
        
        if high_price > pos["highest_price"]:
            pos["highest_price"] = high_price
            
        entry_price = pos["entry_price"]
        stop_loss = pos["stop_loss"]
        tp1 = pos["tp1"]
        tp2 = pos["tp2"]
        now_iso = get_current_utc().isoformat()
        
        # 1. Check Stop Loss Trigger
        if low_price <= stop_loss:
            exec_price = stop_loss * (1.0 - SLIPPAGE_RATE)
            close_qty = pos["remaining_quantity"]
            gross_return = close_qty * exec_price
            exit_fee = gross_return * SPOT_FEE_RATE
            net_return = gross_return - exit_fee
            
            cost_basis = pos["remaining_cost_usdt"]
            entry_fee_portion = pos["fees_paid"] * (close_qty / pos["initial_quantity"])
            total_fees = entry_fee_portion + exit_fee
            leg_pnl_usdt = net_return - cost_basis
            
            self.state["cash_usdt"] += net_return
            
            pos["sl_hit_time"] = now_iso
            pos["sl_exit_price"] = exec_price
            pos["exit_time"] = now_iso
            pos["exit_reason"] = "BREAKEVEN_SL" if pos["tp1_reached"] else "STOP_LOSS"
            
            total_net_pnl = pos["realized_pnl_usdt"] + leg_pnl_usdt
            total_cost = pos["initial_cost_usdt"]
            net_pnl_pct = (total_net_pnl / total_cost) * 100.0 if total_cost > 0 else 0.0
            total_all_fees = pos.get("total_fees_paid", pos["fees_paid"]) + exit_fee
            
            pos["status"] = "WIN" if total_net_pnl > 0 else ("LOSS" if total_net_pnl < 0 else "BREAKEVEN")
            pos["net_pnl_usdt"] = round(total_net_pnl, 4)
            pos["net_pnl_pct"] = round(net_pnl_pct, 2)
            pos["fees_paid"] = round(total_all_fees, 4)
            pos["remaining_quantity"] = 0.0
            pos["remaining_cost_usdt"] = 0.0
            
            # Archive single unified trade
            trade_record = dict(pos)
            self.trade_history.append(trade_record)
            del self.state["open_positions"][symbol]
            self.save()
            return {"event": "CLOSE", "trade": trade_record, "reason": pos["exit_reason"]}

        # 2. Check TP Targets
        # Case A: Price reached or exceeded TP2 (Full Win)
        if high_price >= tp2:
            # If TP1 was not yet recorded, execute TP1 first, then TP2
            if not pos["tp1_reached"]:
                tp1_exec_price = tp1 * (1.0 - SLIPPAGE_RATE)
                tp1_qty = pos["initial_quantity"] * 0.50
                tp1_gross = tp1_qty * tp1_exec_price
                tp1_exit_fee = tp1_gross * SPOT_FEE_RATE
                tp1_net = tp1_gross - tp1_exit_fee
                tp1_cost = pos["initial_cost_usdt"] * 0.50
                tp1_entry_fee = pos["fees_paid"] * 0.50
                tp1_leg_pnl = tp1_net - tp1_cost
                
                self.state["cash_usdt"] += tp1_net
                pos["tp1_reached"] = True
                pos["tp1_hit_time"] = now_iso
                pos["tp1_exit_price"] = tp1_exec_price
                pos["remaining_quantity"] -= tp1_qty
                pos["quantity"] = pos["remaining_quantity"]
                pos["remaining_cost_usdt"] -= tp1_cost
                pos["realized_pnl_usdt"] += tp1_leg_pnl
                pos["total_fees_paid"] = pos.get("total_fees_paid", pos["fees_paid"]) + tp1_exit_fee

            # Now execute TP2 on remaining position
            tp2_exec_price = tp2 * (1.0 - SLIPPAGE_RATE)
            close_qty = pos["remaining_quantity"]
            gross_return = close_qty * tp2_exec_price
            exit_fee = gross_return * SPOT_FEE_RATE
            net_return = gross_return - exit_fee
            
            cost_basis = pos["remaining_cost_usdt"]
            leg_pnl_usdt = net_return - cost_basis
            
            self.state["cash_usdt"] += net_return
            pos["tp2_reached"] = True
            pos["tp2_hit_time"] = now_iso
            pos["tp2_exit_price"] = tp2_exec_price
            pos["exit_time"] = now_iso
            pos["exit_reason"] = "TP2_HIT_FULL"
            
            total_net_pnl = pos["realized_pnl_usdt"] + leg_pnl_usdt
            total_cost = pos["initial_cost_usdt"]
            net_pnl_pct = (total_net_pnl / total_cost) * 100.0 if total_cost > 0 else 0.0
            total_all_fees = pos.get("total_fees_paid", pos["fees_paid"]) + exit_fee
            
            pos["status"] = "WIN"
            pos["net_pnl_usdt"] = round(total_net_pnl, 4)
            pos["net_pnl_pct"] = round(net_pnl_pct, 2)
            pos["fees_paid"] = round(total_all_fees, 4)
            pos["remaining_quantity"] = 0.0
            pos["remaining_cost_usdt"] = 0.0
            
            # Archive single unified trade
            trade_record = dict(pos)
            self.trade_history.append(trade_record)
            del self.state["open_positions"][symbol]
            self.save()
            return {"event": "CLOSE", "trade": trade_record, "reason": "TP2_HIT_FULL"}

        # Case B: Price reached TP1 only (Milestone 50% profit lock)
        if not pos["tp1_reached"] and high_price >= tp1:
            exec_price = tp1 * (1.0 - SLIPPAGE_RATE)
            close_qty = pos["initial_quantity"] * 0.50
            gross_return = close_qty * exec_price
            exit_fee = gross_return * SPOT_FEE_RATE
            net_return = gross_return - exit_fee
            
            cost_basis = pos["initial_cost_usdt"] * 0.50
            entry_fee_portion = pos["fees_paid"] * 0.50
            total_fees = entry_fee_portion + exit_fee
            leg_pnl_usdt = net_return - cost_basis
            
            self.state["cash_usdt"] += net_return
            pos["tp1_reached"] = True
            pos["tp1_hit_time"] = now_iso
            pos["tp1_exit_price"] = exec_price
            pos["remaining_quantity"] -= close_qty
            pos["quantity"] = pos["remaining_quantity"]
            pos["remaining_cost_usdt"] -= cost_basis
            pos["realized_pnl_usdt"] += leg_pnl_usdt
            pos["total_fees_paid"] = pos.get("total_fees_paid", pos["fees_paid"]) + exit_fee
            
            # Move Stop Loss to Breakeven + fee buffer (+0.25%)
            be_sl = entry_price * 1.0025
            if be_sl > pos["stop_loss"]:
                pos["stop_loss"] = be_sl
                
            self.save()
            return {
                "event": "MILESTONE_TP1",
                "symbol": symbol,
                "strategy": pos["strategy"],
                "exit_price": exec_price,
                "pnl_usdt": round(leg_pnl_usdt, 4),
                "pnl_pct": round((leg_pnl_usdt / cost_basis) * 100.0, 2),
                "reason": "TP1_HIT_50PCT"
            }

        self.save()
        return None

    def save(self):
        """Save state and trade history."""
        self.state["last_updated"] = get_current_utc().isoformat()
        self.state_manager.save_state(self.state)
        self.state_manager.save_trade_history(self.trade_history)
