import pandas_ta as ta

def calculate_indicators(df):
    """幫歷史數據加上 5.0 終極版所需的所有技術指標"""
    df.ta.rsi(length=14, append=True)                   # 14日 RSI 找回檔
    df.ta.macd(fast=12, slow=26, signal=9, append=True) # MACD 找轉折動能
    df.ta.sma(length=20, append=True)                   # 20日月線判斷大趨勢
    df.ta.atr(length=14, append=True)                   # 14日真實波動幅度 (ATR停損核心)
    
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
    """在 5.0 架構下，賣出完全交由 main.py 的 ATR 吊燈停損來控管，武官不再亂發警報"""
    return False
