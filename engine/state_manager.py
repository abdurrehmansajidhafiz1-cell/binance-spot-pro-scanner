"""
State Persistence Manager for Paper Trading.
Saves and loads portfolio state and trade history from JSON/SQLite.
Ensures continuity across GitHub Actions runs or script restarts.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Any
from config.settings import STATE_FILE, TRADE_HISTORY_FILE, STARTING_BALANCE_USDT


class StateManager:
    def __init__(self, state_file: Path = STATE_FILE, history_file: Path = TRADE_HISTORY_FILE):
        self.state_file = state_file
        self.history_file = history_file

    def load_state(self) -> Dict[str, Any]:
        """Load portfolio state or initialize with default."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        
        default_state = {
            "cash_usdt": STARTING_BALANCE_USDT,
            "starting_balance": STARTING_BALANCE_USDT,
            "equity_peak": STARTING_BALANCE_USDT,
            "open_positions": {},  # symbol -> position dict
            "start_time": None,
            "last_updated": None
        }
        return default_state

    def save_state(self, state: Dict[str, Any]):
        """Persist portfolio state to JSON."""
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def load_trade_history(self) -> List[Dict[str, Any]]:
        """Load closed trade history."""
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def save_trade_history(self, history: List[Dict[str, Any]]):
        """Append and persist closed trades."""
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
