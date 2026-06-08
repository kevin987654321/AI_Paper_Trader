import pandas as pd
import os
import config
from datetime import datetime

def init_ledger():
    """如果帳本不存在，或是檔案大小為 0 (空白檔案)，就初始化一個新的"""
    # 檢查條件：檔案不存在，或者檔案存在但是空的 (0 KB)
    if not os.path.exists(config.LEDGER_PATH) or os.stat(config.LEDGER_PATH).st_size == 0:
        
        # 確保 data 資料夾存在
        os.makedirs(os.path.dirname(config.LEDGER_PATH), exist_ok=True)
        
        # 建立欄位
        df = pd.DataFrame(columns=["Date", "Action", "Ticker", "Price", "Shares", "Total_Value", "Cash_Left"])
        # 存入 10 萬初始本金
        df.loc[0] = [datetime.now().strftime("%Y-%m-%d %H:%M"), "DEPOSIT", "NONE", 0, 0, config.INITIAL_CAPITAL, config.INITIAL_CAPITAL]
        
        # 寫入檔案
        df.to_csv(config.LEDGER_PATH, index=False)
        print("✅ 虛擬帳本初始化完成，已存入初始本金。")

def get_current_cash():
    """讀取帳本，看還剩多少現金"""
    df = pd.read_csv(config.LEDGER_PATH)
    return df.iloc[-1]["Cash_Left"]

def log_trade(action, ticker, price, shares):
    """把交易寫入 CSV 帳本"""
    df = pd.read_csv(config.LEDGER_PATH)
    current_cash = df.iloc[-1]["Cash_Left"]
    
    trade_value = price * shares
    if action == "BUY":
        new_cash = current_cash - trade_value
    elif action == "SELL":
        new_cash = current_cash + trade_value
    else:
        return
        
    new_row = [datetime.now().strftime("%Y-%m-%d %H:%M"), action, ticker, price, shares, trade_value, new_cash]
    df.loc[len(df)] = new_row
    df.to_csv(config.LEDGER_PATH, index=False)
    print(f"✅ 成功寫入虛擬帳本：{action} {shares} 股 {ticker} @ {price} 元。剩餘現金：{new_cash}")