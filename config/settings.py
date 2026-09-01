"""
Configuration settings for Binance Spot Live Paper Trading Scanner.
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Data & Storage Directories
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

STATE_FILE = DATA_DIR / "portfolio_state.json"
TRADE_HISTORY_FILE = DATA_DIR / "trade_history.json"
LIVE_RESULTS_MD = BASE_DIR / "LIVE_RESULTS.md"
COINS_UNIVERSE_FILE = BASE_DIR / "config" / "coins_universe.json"

# Load Universe
if COINS_UNIVERSE_FILE.exists():
    with open(COINS_UNIVERSE_FILE, "r", encoding="utf-8") as f:
        COINS_UNIVERSE = json.load(f)
else:
    COINS_UNIVERSE = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]

# Paper Broker & Account Settings
STARTING_BALANCE_USDT = float(os.getenv("STARTING_BALANCE", 10000.0))
SPOT_FEE_RATE = float(os.getenv("SPOT_FEE_RATE", 0.00075)) # 0.075% with BNB discount (VIP0)
SLIPPAGE_RATE = float(os.getenv("SLIPPAGE_RATE", 0.00050)) # 0.05% realistic slippage
MAX_CONCURRENT_POSITIONS = int(os.getenv("MAX_CONCURRENT_POSITIONS", 5))
RISK_PER_TRADE_PCT = float(os.getenv("RISK_PER_TRADE_PCT", 0.015)) # 1.5% portfolio risk per trade

# Email Notification Settings (Actionable 100 USDT Trade Plans)
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "").strip()
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", "").strip()
ENABLE_EMAIL = bool(SENDER_EMAIL and GMAIL_APP_PASSWORD and RECEIVER_EMAIL)

# Telegram Notification Settings (Optional)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
ENABLE_TELEGRAM = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)

# Strategy Timeframes & Parameters
TIMEFRAME_S3 = "15m"      # S3: Volatility Squeeze Breakout
TIMEFRAME_I1_EXEC = "1h"  # I1: Multi-Timeframe Pullback (Execution)
TIMEFRAME_I1_TREND = "4h" # I1: Multi-Timeframe Pullback (Macro Trend)
TIMEFRAME_I2_RANK = "1d"  # I2: Cross-Sectional Momentum (Ranking)
TIMEFRAME_I2_EXEC = "4h"  # I2: Execution & Rebalance

# Binance Public REST Base URL
BINANCE_API_BASE = "https://api.binance.com"
