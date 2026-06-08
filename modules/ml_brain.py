import pandas_ta as ta

def calculate_indicators(df):
    """幫歷史數據加上技術指標"""
    # 計算 14 日 RSI (相對強弱指標)
    df.ta.rsi(length=14, append=True)
    # 計算 MACD (快線 12, 慢線 26, 訊號線 9)
    df.ta.macd(fast=12, slow=26, signal=9, append=True)
    
    # 刪除因為計算指標而產生的 NaN 空白列
    df.dropna(inplace=True)
    return df

def check_buy_signal(df):
    """
    判斷現在是不是該買進？
    回傳 True (買進) 或 False (觀望)
    """
    if df is None or len(df) < 2:
        return False

    # 取得最新一天的數據
    latest = df.iloc[-1]
    
    # 檢查欄位是否存在，避免因為數據不足報錯
    if 'RSI_14' not in latest or 'MACD_12_26_9' not in latest:
        return False

    rsi = latest['RSI_14']
    macd = latest['MACD_12_26_9']
    macd_signal = latest['MACDs_12_26_9']

    # 策略邏輯：超賣抄底 + 動能反轉
    if rsi < 35 and macd > macd_signal:
        print(f"💡 [武官判定] 強烈買進訊號！RSI={rsi:.1f} (超賣區) 且 MACD 呈現黃金交叉。")
        return True
    
    return False

def check_sell_signal(df):
    """
    判斷現在是不是該賣出？(停利機制)
    """
    if df is None or len(df) < 2:
        return False
        
    latest = df.iloc[-1]
    
    if 'RSI_14' not in latest:
        return False
        
    rsi = latest['RSI_14']
    
    # 策略邏輯：RSI > 75 代表極度過熱，準備獲利了結
    if rsi > 75:
        print(f"💡 [武官判定] 過熱賣出訊號！RSI={rsi:.1f} (超買區)。")
        return True
        
    return False
