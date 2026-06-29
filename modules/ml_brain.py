import pandas as pd
import numpy as np

def calculate_indicators(df):
    """完全擺脫 pandas-ta 依賴地獄！使用純 Pandas 手工精準打造 5 核心指標"""
    df = df.copy()
    
    # 1. 20日月線 (SMA_20)
    df['SMA_20'] = df['Close'].rolling(window=20).mean()

    # 2. 14日 RSI (使用 Wilder's Smoothing)
    delta = df['Close'].diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    loss = -delta.clip(upper=0).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = gain / loss
    df['RSI_14'] = 100 - (100 / (1 + rs))

    # 3. MACD (12, 26, 9)
    ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD_12_26_9'] = ema_12 - ema_26
    df['MACDs_12_26_9'] = df['MACD_12_26_9'].ewm(span=9, adjust=False).mean()

    # 4. 14日 ATR (真實波動幅度)
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATRr_14'] = true_range.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

    df.dropna(inplace=True)
    return df

def check_buy_signal(df):
    """
    判斷技術面是否符合進場條件：
    1. 站上月線 (多頭趨勢)
    2. RSI < 55 (短線回檔相對低點)
    3. MACD 處於剛黃金交叉或開口向上的階段
    """
    if df is None or len(df) < 2:
        return False

    latest = df.iloc[-1]
    
    if 'SMA_20' not in latest or 'ATRr_14' not in latest:
        return False

    macd_diff = latest['MACD_12_26_9'] - latest['MACDs_12_26_9']
    
    if (latest['Close'] > latest['SMA_20']) and (latest['RSI_14'] < 55) and (macd_diff > 0) and (macd_diff < 5):
        return True
        
    return False

def check_sell_signal(df):
    """在 5.0 架構下，賣出交由 main.py 的 ATR 吊燈停損來控管"""
    return False
