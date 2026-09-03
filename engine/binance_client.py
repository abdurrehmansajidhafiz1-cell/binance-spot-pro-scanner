"""
Binance Spot REST API Client for fetching public market data (OHLCV, Taker Volume, Prices).
Zero API keys required for public endpoints.
"""
import time
import requests
import pandas as pd
from typing import Optional, List, Dict
from config.settings import BINANCE_API_BASE


FALLBACK_BASES = [
    "https://data-api.binance.vision",
    "https://api1.binance.com",
    "https://api3.binance.com",
    "https://api.binance.com"
]


class BinanceSpotClient:
    def __init__(self, base_url: str = BINANCE_API_BASE, timeout: int = 15):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        })

    def _get_base_urls(self) -> List[str]:
        """Return list of base URLs with primary first, followed by fallbacks."""
        urls = [self.base_url]
        for fb in FALLBACK_BASES:
            if fb not in urls:
                urls.append(fb)
        return urls

    def get_klines(self, symbol: str, interval: str, limit: int = 250) -> pd.DataFrame:
        """
        Fetch OHLCV klines with taker volume from Binance Spot.
        Tries primary endpoint and fallbacks automatically.
        """
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": limit
        }
        
        for base in self._get_base_urls():
            endpoint = f"{base}/api/v3/klines"
            for attempt in range(2):
                try:
                    response = self.session.get(endpoint, params=params, timeout=self.timeout)
                    if response.status_code == 200:
                        data = response.json()
                        if not data:
                            return pd.DataFrame()
                            
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
                        time.sleep(2 * (attempt + 1))
                    else:
                        time.sleep(1)
                except Exception:
                    time.sleep(1)
                    
        return pd.DataFrame()

    def get_24h_tickers(self) -> Dict[str, Dict]:
        """Fetch 24h ticker price change and quote volume for all symbols.
        Tries non-geoblocked data-api.binance.vision first with automatic failover.
        """
        for base in self._get_base_urls():
            endpoint = f"{base}/api/v3/ticker/24hr"
            for attempt in range(2):
                try:
                    resp = self.session.get(endpoint, timeout=25)
                    if resp.status_code == 200:
                        data = resp.json()
                        result = {
                            item["symbol"]: {
                                "last_price": float(item["lastPrice"]),
                                "quote_volume": float(item["quoteVolume"]),
                                "price_change_pct": float(item["priceChangePercent"])
                            }
                            for item in data if item["symbol"].endswith("USDT")
                        }
                        if result and len(result) > 50:
                            return result
                    elif resp.status_code == 429:
                        time.sleep(2)
                    else:
                        print(f"  [API NOTICE] {base} returned status {resp.status_code}. Trying failover...")
                        break
                except Exception as e:
                    print(f"  [API NOTICE] {base} connection error: {e}. Trying failover...")
                    break
        return {}

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Fetch real-time ticker price for a single symbol with fallback."""
        for base in self._get_base_urls():
            endpoint = f"{base}/api/v3/ticker/price"
            try:
                resp = self.session.get(endpoint, params={"symbol": symbol.upper()}, timeout=8)
                if resp.status_code == 200:
                    return float(resp.json()["price"])
            except Exception:
                continue
        return None
