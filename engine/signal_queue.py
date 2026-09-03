"""
engine/signal_queue.py
Persistent Signal Queue - saves detected signals to disk so they survive
across cycles. If a signal fires but execution fails (API error, tickers empty,
etc.), it is queued and retried on the next cron run, as long as price is still
valid (not past SL/TP and within max age).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Optional

from config.settings import DATA_DIR

QUEUE_FILE = DATA_DIR / "pending_signals.json"

# Max age before a signal is considered stale and auto-discarded
MAX_AGE_S3_HOURS = 2    # S3 is a short-term 15m setup - expire after 2h
MAX_AGE_I1_HOURS = 12   # I1 is a 1h/4h setup - give it 12 hours

# Max % deviation from entry before we consider setup "over-extended"
MAX_ENTRY_DEVIATION_PCT = 2.0


class SignalQueue:
    """Load, save, validate, and expire pending signals."""

    def __init__(self):
        self._queue: List[Dict] = self._load()

    def _load(self) -> List[Dict]:
        try:
            if QUEUE_FILE.exists():
                with open(QUEUE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
        except Exception:
            pass
        return []

    def _save(self):
        try:
            with open(QUEUE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._queue, f, indent=2)
        except Exception:
            pass

    def enqueue(self, signal_dict: Dict):
        """Add a new pending signal (deduplicated by symbol)."""
        self._queue = [s for s in self._queue if s.get("symbol") != signal_dict["symbol"]]
        signal_dict["queued_at"] = datetime.now(timezone.utc).isoformat()
        self._queue.append(signal_dict)
        self._save()
        print(f"  [SIGNAL QUEUED] {signal_dict['symbol']} saved to pending queue for next cycle.")

    def remove(self, symbol: str):
        """Remove a signal after successful execution or expiry."""
        self._queue = [s for s in self._queue if s.get("symbol") != symbol]
        self._save()

    def get_valid_pending(self, current_prices: Dict[str, float]) -> List[Dict]:
        """
        Return pending signals that are still tradeable right now.
        Filters out: expired (too old), SL hit, TP2 hit, over-extended.
        """
        now_utc = datetime.now(timezone.utc)
        valid = []
        expired = []

        for sig in self._queue:
            symbol = sig.get("symbol", "")
            strategy = sig.get("strategy", "")
            entry = sig.get("entry_price", 0.0)
            sl = sig.get("stop_loss", 0.0)
            tp2 = sig.get("tp2", 0.0)
            queued_at_str = sig.get("queued_at", now_utc.isoformat())

            try:
                queued_at = datetime.fromisoformat(queued_at_str)
                if queued_at.tzinfo is None:
                    queued_at = queued_at.replace(tzinfo=timezone.utc)
            except Exception:
                queued_at = now_utc

            age_hours = (now_utc - queued_at).total_seconds() / 3600.0
            max_age = MAX_AGE_I1_HOURS if "I1" in strategy.upper() else MAX_AGE_S3_HOURS

            if age_hours > max_age:
                print(f"  [QUEUE EXPIRE] {symbol} - signal too old ({age_hours:.1f}h > {max_age}h). Discarding.")
                expired.append(symbol)
                continue

            curr_p = current_prices.get(symbol)
            if not curr_p:
                continue  # Keep in queue, no price available yet

            if curr_p <= sl:
                print(f"  [QUEUE EXPIRE] {symbol} - price ${curr_p:.4f} hit SL ${sl:.4f}. Discarding.")
                expired.append(symbol)
                continue

            if curr_p >= tp2:
                print(f"  [QUEUE EXPIRE] {symbol} - price ${curr_p:.4f} past TP2 ${tp2:.4f}. Discarding.")
                expired.append(symbol)
                continue

            deviation_pct = abs((curr_p - entry) / entry) * 100
            if deviation_pct > MAX_ENTRY_DEVIATION_PCT and curr_p > entry:
                print(f"  [QUEUE STALE] {symbol} - price moved {deviation_pct:.1f}% from entry. Discarding.")
                expired.append(symbol)
                continue

            sig_copy = dict(sig)
            sig_copy["current_price_now"] = curr_p
            valid.append(sig_copy)

        for sym in expired:
            self.remove(sym)

        return valid

    def __len__(self):
        return len(self._queue)

    def pending_symbols(self) -> List[str]:
        return [s.get("symbol", "") for s in self._queue]
