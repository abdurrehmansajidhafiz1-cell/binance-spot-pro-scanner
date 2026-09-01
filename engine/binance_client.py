"""
Binance Spot REST API Client for fetching public market data (OHLCV, Taker Volume, Prices).
Zero API keys required for public endpoints.
"""
import time
import requests
import pandas as pd
from typing import Optional, List, Dict
from config.settings import BINANCE_API_BASE


class BinanceSpotClient:
    def __init__(self, base_url: str = BINANCE_API_BASE, timeout: int = 10):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "BinanceSpotScanner/1.0",
            "Accept": "application/json"
        })

    def get_klines(self, symbol: str, interval: str, limit: int = 250) -> pd.DataFrame:
        """
        Fetch OHLCV klines with taker volume from Binance Spot.
        Intervals: 1m, 3m, 5m, 15m, 30m, 1h, 4h, 1d.
        """
        endpoint = f"{self.base_url}/api/v3/klines"
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": limit
        }
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.session.get(endpoint, params=params, timeout=self.timeout)
                if response.status_code == 200:
                    data = response.json()
                    if not data:
                        return pd.DataFrame()
                        
                    # Binance Kline schema:
                    # 0: Open time, 1: Open, 2: High, 3: Low, 4: Close, 5: Volume,
                    # 6: Close time, 7: Quote asset volume, 8: Number of trades,
                    # 9: Taker buy base asset volume, 10: Taker buy quote asset volume, 11: Ignore
                    df = pd.DataFrame(data, columns=[
                        "open_time", "open", "high", "low", "close", "volume",
                        "close_time", "quote_volume", "trades",
                        "taker_buy_base_volume", "taker_buy_quote_volume", "ignore"
                    ])
                    
                    numeric_cols = ["open", "high", "low", "close", "volume", "quote_volume", "taker_buy_base_volume", "taker_buy_quote_volume"]
                    for col in numeric_cols:
                        df[col] = df[col].astype(float)
                        
                    df["trades"] = df["trades"].astype(int)
                    df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms")
                    df.set_index("timestamp", inplace=True)
                    return df
                    
                elif response.status_code == 429:
                    # Rate limit hit, backoff
                    time.sleep(2 * (attempt + 1))
                else:
                    time.sleep(1)
            except Exception as e:
                time.sleep(1 * (attempt + 1))
                
        return pd.DataFrame()

    def get_24h_tickers(self) -> Dict[str, Dict]:
        """Fetch 24h ticker price change and quote volume for all symbols."""
        endpoint = f"{self.base_url}/api/v3/ticker/24hr"
        try:
            resp = self.session.get(endpoint, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    item["symbol"]: {
                        "last_price": float(item["lastPrice"]),
                        "quote_volume": float(item["quoteVolume"]),
                        "price_change_pct": float(item["priceChangePercent"])
                    }
                    for item in data if item["symbol"].endswith("USDT")
                }
        except Exception:
            pass
        return {}

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Fetch real-time ticker price for a single symbol."""
        endpoint = f"{self.base_url}/api/v3/ticker/price"
        try:
            resp = self.session.get(endpoint, params={"symbol": symbol.upper()}, timeout=self.timeout)
            if resp.status_code == 200:
                return float(resp.json()["price"])
        except Exception:
            pass
        return None
