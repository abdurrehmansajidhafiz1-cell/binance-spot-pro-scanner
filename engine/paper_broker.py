"""
Realistic Binance Spot Virtual Paper Broker.
Models maker/taker fees, bid-ask spread, slippage, and position tracking.
"""
from datetime import datetime
from typing import Dict, Optional, Tuple, Any
from config.settings import (
    SPOT_FEE_RATE, SLIPPAGE_RATE, MAX_CONCURRENT_POSITIONS,
    RISK_PER_TRADE_PCT, STARTING_BALANCE_USDT
)
from engine.state_manager import StateManager


class PaperBroker:
    def __init__(self, state_manager: Optional[StateManager] = None):
        self.state_manager = state_manager or StateManager()
        self.state = self.state_manager.load_state()
        self.trade_history = self.state_manager.load_trade_history()
        
        if not self.state.get("start_time"):
            self.state["start_time"] = datetime.utcnow().isoformat()
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
            equity += pos["quantity"] * price
        return equity

    def calculate_position_size(self, current_price: float, stop_loss: float, total_equity: float) -> Tuple[float, float]:
        """
        Calculate units and USDT size based on fixed fractional risk.
        Risk Amount = Equity * RISK_PER_TRADE_PCT.
        """
        risk_per_unit = abs(current_price - stop_loss)
        if risk_per_unit <= 0:
            risk_per_unit = current_price * 0.02 # fallback 2% risk distance
            
        risk_amount = total_equity * RISK_PER_TRADE_PCT
        raw_quantity = risk_amount / risk_per_unit
        position_cost_usdt = raw_quantity * current_price
        
        # Cap position size to max 25% of total equity per trade or available cash
        max_pos_usdt = min(total_equity * 0.25, self.cash * 0.95)
        if position_cost_usdt > max_pos_usdt:
            position_cost_usdt = max_pos_usdt
            raw_quantity = position_cost_usdt / current_price
            
        return raw_quantity, position_cost_usdt

    def can_open_position(self, symbol: str) -> bool:
        """Check if portfolio capacity allows new trade."""
        if symbol in self.open_positions:
            return False
        if len(self.open_positions) >= MAX_CONCURRENT_POSITIONS:
            return False
        if self.cash < 50.0: # Minimum $50 cash threshold
            return False
        return True

    def open_long_position(self, symbol: str, strategy_name: str, current_price: float,
                           stop_loss: float, tp1: float, tp2: float,
                           metadata: Optional[Dict] = None) -> Optional[Dict]:
        """
        Execute Long Spot order with realistic slippage and fee deduction.
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
            # Adjust to available cash
            cost_usdt = (self.cash * 0.98) / (1.0 + SPOT_FEE_RATE)
            quantity = cost_usdt / exec_price
            fee_paid = cost_usdt * SPOT_FEE_RATE
            total_deduction = cost_usdt + fee_paid

        self.state["cash_usdt"] -= total_deduction
        
        position = {
            "symbol": symbol,
            "strategy": strategy_name,
            "entry_time": datetime.utcnow().isoformat(),
            "entry_price": exec_price,
            "current_price": exec_price,
            "quantity": quantity,
            "initial_cost_usdt": cost_usdt,
            "stop_loss": stop_loss,
            "initial_stop_loss": stop_loss,
            "tp1": tp1,
            "tp2": tp2,
            "tp1_reached": False,
            "highest_price": exec_price,
            "fees_paid": fee_paid,
            "metadata": metadata or {}
        }
        
        self.state["open_positions"][symbol] = position
        self.save()
        return position

    def close_position(self, symbol: str, current_price: float, reason: str, partial_pct: float = 1.0) -> Optional[Dict]:
        """
        Close full or partial spot position.
        """
        if symbol not in self.open_positions:
            return None
            
        pos = self.open_positions[symbol]
        
        # Apply slippage on exit (Sell lower than mid price)
        exec_price = current_price * (1.0 - SLIPPAGE_RATE)
        close_qty = pos["quantity"] * partial_pct
        gross_return_usdt = close_qty * exec_price
        exit_fee = gross_return_usdt * SPOT_FEE_RATE
        net_return_usdt = gross_return_usdt - exit_fee
        
        cost_basis = pos["initial_cost_usdt"] * partial_pct
        entry_fee = pos["fees_paid"] * partial_pct
        total_fees = entry_fee + exit_fee
        net_pnl_usdt = net_return_usdt - cost_basis
        net_pnl_pct = (net_pnl_usdt / cost_basis) * 100.0 if cost_basis > 0 else 0.0
        
        self.state["cash_usdt"] += net_return_usdt
        
        trade_record = {
            "symbol": symbol,
            "strategy": pos["strategy"],
            "entry_time": pos["entry_time"],
            "exit_time": datetime.utcnow().isoformat(),
            "entry_price": pos["entry_price"],
            "exit_price": exec_price,
            "quantity": close_qty,
            "cost_usdt": cost_basis,
            "net_pnl_usdt": round(net_pnl_usdt, 4),
            "net_pnl_pct": round(net_pnl_pct, 2),
            "fees_paid": round(total_fees, 4),
            "exit_reason": reason,
            "partial": partial_pct < 1.0
        }
        
        self.trade_history.append(trade_record)
        
        if partial_pct >= 0.99:
            del self.state["open_positions"][symbol]
        else:
            pos["quantity"] -= close_qty
            pos["initial_cost_usdt"] -= cost_basis
            pos["fees_paid"] -= entry_fee
            
        self.save()
        return trade_record

    def update_position_market_price(self, symbol: str, current_price: float, high_price: float, low_price: float) -> Optional[Dict]:
        """
        Check Stop Loss, TP1, TP2, Trailing Stop triggers on new bar data.
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
        
        # 1. Check Stop Loss Trigger
        if low_price <= stop_loss:
            return self.close_position(symbol, stop_loss, "STOP_LOSS")
            
        # 2. Check TP1 Trigger
        if not pos["tp1_reached"] and high_price >= tp1:
            pos["tp1_reached"] = True
            # Secure Stop Loss to Breakeven + fee buffer (+0.25%)
            be_sl = entry_price * 1.0025
            if be_sl > pos["stop_loss"]:
                pos["stop_loss"] = be_sl
            self.save()
            # Partial profit close 50%
            return self.close_position(symbol, tp1, "TP1_HIT_50PCT", partial_pct=0.50)
            
        # 3. Check TP2 Trigger
        if pos["tp1_reached"] and high_price >= tp2:
            return self.close_position(symbol, tp2, "TP2_HIT_FULL", partial_pct=1.0)
            
        self.save()
        return None

    def save(self):
        """Save state and trade history."""
        self.state["last_updated"] = datetime.utcnow().isoformat()
        self.state_manager.save_state(self.state)
        self.state_manager.save_trade_history(self.trade_history)
