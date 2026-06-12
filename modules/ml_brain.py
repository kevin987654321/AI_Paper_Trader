import pandas_ta as ta

def calculate_indicators(df):
    """幫歷史數據加上技術指標"""
    # 🏆 根據最佳化回測結果：改為計算 21 日 RSI 以過濾雜訊
    df.ta.rsi(length=21, append=True)
    # 計算 MACD (快線 12, 慢線 26, 訊號線 9) - 維持不變的最強防禦設定
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
    
    # ⚠️ 注意這裡檢查的欄位要改成 RSI_21
    if 'RSI_21' not in latest or 'MACD_12_26_9' not in latest:
        return False

    rsi = latest['RSI_21']
    macd = latest['MACD_12_26_9']
    macd_signal = latest['MACDs_12_26_9']

    # 🏆 策略邏輯升級：放寬打擊區 (RSI < 55) + 動能反轉
    if rsi < 55 and macd > macd_signal:
        print(f"💡 [武官判定] 強烈買進訊號！RSI={rsi:.1f} (小幅回檔區) 且 MACD 呈現黃金交叉。")
        return True
    
    return False

def check_sell_signal(df):
    """
    判斷現在是不是該賣出？(停利機制：動能衰退才賣)
    """
    if df is None or len(df) < 2:
        return False
        
    latest = df.iloc[-1]
    
    # 檢查 MACD 欄位是否存在
    if 'MACD_12_26_9' not in latest or 'MACDs_12_26_9' not in latest:
        return False
        
    macd = latest['MACD_12_26_9']
    macd_signal = latest['MACDs_12_26_9']
    
    # 策略邏輯：MACD 死亡交叉 (快線跌破慢線)，代表上漲動能消失，準備獲利了結或提早拔檔
    if macd < macd_signal:
        print(f"💡 [武官判定] 動能轉弱賣出訊號！MACD 出現死亡交叉。")
        return True
        
    return False
