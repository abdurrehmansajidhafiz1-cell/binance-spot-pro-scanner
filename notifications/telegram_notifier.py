"""
Optional Telegram Notification Service.
Sends formatted alerts on Buy, Stop Loss, Take Profit, and Daily Performance.
"""
import requests
from typing import Optional
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ENABLE_TELEGRAM


class TelegramNotifier:
    def __init__(self, token: str = TELEGRAM_BOT_TOKEN, chat_id: str = TELEGRAM_CHAT_ID):
        self.token = token
        self.chat_id = chat_id
        self.enabled = ENABLE_TELEGRAM and bool(self.token and self.chat_id)

    def send_message(self, text: str) -> bool:
        if not self.enabled:
            return False
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        try:
            resp = requests.post(url, json=payload, timeout=8)
            return resp.status_code == 200
        except Exception:
            return False

    def alert_buy(self, symbol: str, strategy: str, price: float, sl: float, tp1: float, tp2: float, reason: str):
        msg = (
            f"🟢 *BINANCE SPOT SIGNAL — BUY*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🪙 *Symbol:* `{symbol}`\n"
            f"🧠 *Strategy:* `{strategy}`\n"
            f"💵 *Entry Price:* `${price:,.4f}`\n"
            f"🛑 *Stop Loss:* `${sl:,.4f}` (-{((price-sl)/price)*100:.2f}%)\n"
            f"🎯 *TP1 (50%):* `${tp1:,.4f}` (+{((tp1-price)/price)*100:.2f}%)\n"
            f"🎯 *TP2 (50%):* `${tp2:,.4f}` (+{((tp2-price)/price)*100:.2f}%)\n"
            f"📝 *Reason:* {reason}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        return self.send_message(msg)

    def alert_close(self, symbol: str, strategy: str, exit_price: float, pnl_usdt: float, pnl_pct: float, reason: str):
        icon = "🎉" if pnl_usdt >= 0 else "🛑"
        msg = (
            f"{icon} *TRADE CLOSED — {symbol}*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🧠 *Strategy:* `{strategy}`\n"
            f"💵 *Exit Price:* `${exit_price:,.4f}`\n"
            f"📊 *Net PnL:* `${pnl_usdt:+,.2f} ({pnl_pct:+.2f}%)`\n"
            f"📌 *Exit Reason:* `{reason}`\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        return self.send_message(msg)
