"""
Vectorized Quantitative & Technical Indicators using NumPy and Pandas.
Optimized for zero-lag calculations across 50 coins.
"""
import numpy as np
import pandas as pd


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period).mean()


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range (ATR)."""
    high = df['high']
    low = df['low']
    close = df['close']
    prev_close = close.shift(1)
    
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0/period, adjust=False).mean()


def calculate_bollinger_bands(series: pd.Series, period: int = 20, num_std: float = 2.0):
    """Bollinger Bands."""
    sma = calculate_sma(series, period)
    rolling_std = series.rolling(window=period).std()
    upper = sma + (rolling_std * num_std)
    lower = sma - (rolling_std * num_std)
    return upper, sma, lower


def calculate_keltner_channels(df: pd.DataFrame, period: int = 20, atr_mult: float = 1.5, atr_period: int = 20):
    """Keltner Channels using EMA and ATR."""
    ema = calculate_ema(df['close'], period)
    atr = calculate_atr(df, atr_period)
    upper = ema + (atr * atr_mult)
    lower = ema - (atr * atr_mult)
    return upper, ema, lower


def calculate_squeeze(df: pd.DataFrame, bb_period: int = 20, bb_std: float = 2.0, kc_period: int = 20, kc_mult: float = 1.5):
    """
    Bollinger Bands vs Keltner Channels Squeeze Indicator.
    Returns:
      - is_squeeze: Boolean Series (True when BB is inside KC)
      - bb_upper, bb_mid, bb_lower
      - kc_upper, kc_mid, kc_lower
      - mom_hist: Linear regression / momentum histogram
    """
    bb_upper, bb_mid, bb_lower = calculate_bollinger_bands(df['close'], bb_period, bb_std)
    kc_upper, kc_mid, kc_lower = calculate_keltner_channels(df, kc_period, kc_mult, kc_period)
    
    # Squeeze is active when BB is entirely inside KC
    is_squeeze = (bb_upper < kc_upper) & (bb_lower > kc_lower)
    
    # Linear momentum calculation: distance from average of Donchian midline and SMA
    donchian_mid = (df['high'].rolling(kc_period).max() + df['low'].rolling(kc_period).min()) / 2.0
    sma_mid = calculate_sma(df['close'], kc_period)
    delta = df['close'] - ((donchian_mid + sma_mid) / 2.0)
    
    # Fast momentum slope approximation
    mom_hist = calculate_ema(delta, 12)
    
    return is_squeeze, bb_upper, bb_mid, bb_lower, kc_upper, kc_mid, kc_lower, mom_hist


def calculate_obv(df: pd.DataFrame) -> pd.Series:
    """On-Balance Volume (OBV)."""
    close_diff = df['close'].diff()
    direction = np.where(close_diff > 0, 1, np.where(close_diff < 0, -1, 0))
    obv = (direction * df['volume']).cumsum()
    return pd.Series(obv, index=df.index)


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index (RSI)."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    avg_gain = gain.ewm(alpha=1.0/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0/period, adjust=False).mean()
    
    rs = avg_gain / (avg_loss + 1e-10)
    return 100 - (100 / (1 + rs))


def calculate_supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0):
    """
    SuperTrend Indicator (Vectorized + Iterative loop for exact flips).
    Returns:
      - supertrend: Price line
      - direction: 1 for Bullish (Green), -1 for Bearish (Red)
    """
    atr = calculate_atr(df, period)
    hl2 = (df['high'] + df['low']) / 2.0
    
    basic_upper = hl2 + (multiplier * atr)
    basic_lower = hl2 - (multiplier * atr)
    
    final_upper = np.zeros(len(df))
    final_lower = np.zeros(len(df))
    supertrend = np.zeros(len(df))
    direction = np.zeros(len(df), dtype=int)
    
    close = df['close'].values
    b_upper = basic_upper.values
    b_lower = basic_lower.values
    
    for i in range(len(df)):
        if i == 0:
            final_upper[i] = b_upper[i]
            final_lower[i] = b_lower[i]
            direction[i] = 1
            supertrend[i] = final_lower[i]
            continue
            
        # Upper band calculation
        if b_upper[i] < final_upper[i-1] or close[i-1] > final_upper[i-1]:
            final_upper[i] = b_upper[i]
        else:
            final_upper[i] = final_upper[i-1]
            
        # Lower band calculation
        if b_lower[i] > final_lower[i-1] or close[i-1] < final_lower[i-1]:
            final_lower[i] = b_lower[i]
        else:
            final_lower[i] = final_lower[i-1]
            
        # Trend direction evaluation
        if direction[i-1] == 1:
            if close[i] < final_lower[i]:
                direction[i] = -1
                supertrend[i] = final_upper[i]
            else:
                direction[i] = 1
                supertrend[i] = final_lower[i]
        else:
            if close[i] > final_upper[i]:
                direction[i] = 1
                supertrend[i] = final_lower[i]
            else:
                direction[i] = -1
                supertrend[i] = final_upper[i]
                
    return pd.Series(supertrend, index=df.index), pd.Series(direction, index=df.index)


def calculate_adx(df: pd.DataFrame, period: int = 14):
    """Average Directional Index (ADX) + DI+ / DI-."""
    high = df['high']
    low = df['low']
    close = df['close']
    
    up_move = high.diff()
    down_move = -low.diff()
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    tr = calculate_atr(df, 1) # True range
    tr_smooth = tr.rolling(period).sum()
    plus_di = 100 * (pd.Series(plus_dm, index=df.index).rolling(period).sum() / (tr_smooth + 1e-10))
    minus_di = 100 * (pd.Series(minus_dm, index=df.index).rolling(period).sum() / (tr_smooth + 1e-10))
    
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10))
    adx = dx.ewm(alpha=1.0/period, adjust=False).mean()
    
    return adx, plus_di, minus_di
