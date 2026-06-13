import pandas as pd
import os
import config
from datetime import datetime

def init_ledgers():
    """初始化雙軌帳本：一個給 AI 動態，一個給固定參數"""
    # 確保 data 資料夾存在
    os.makedirs(os.path.dirname(config.LEDGER_PATH), exist_ok=True)
    
    ledgers = [
        ("🧠 AI 動態帳本", config.LEDGER_PATH), 
        ("⚖️ 靜態對照帳本", getattr(config, 'LEDGER_STATIC_PATH', "data/paper_ledger_static.csv"))
    ]
    
    for name, path in ledgers:
        if not os.path.exists(path) or os.stat(path).st_size == 0:
            df = pd.DataFrame(columns=["Date", "Action", "Ticker", "Price", "Shares", "Total_Value", "Cash_Left"])
            df.loc[0] = [datetime.now().strftime("%Y-%m-%d %H:%M"), "DEPOSIT", "NONE", 0, 0, config.INITIAL_CAPITAL, config.INITIAL_CAPITAL]
            df.to_csv(path, index=False)
            print(f"✅ {name} 初始化完成。")

def get_current_cash(is_static=False):
    """讀取帳本剩餘現金"""
    path = getattr(config, 'LEDGER_STATIC_PATH', "data/paper_ledger_static.csv") if is_static else config.LEDGER_PATH
    df = pd.read_csv(path)
    return df.iloc[-1]["Cash_Left"]

def log_trade(action, ticker, price, shares, is_static=False):
    """把交易精準寫入對應的 CSV 帳本"""
    target_path = getattr(config, 'LEDGER_STATIC_PATH', "data/paper_ledger_static.csv") if is_static else config.LEDGER_PATH
    
    df = pd.read_csv(target_path)
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
    df.to_csv(target_path, index=False)
    
    mode_str = "靜態對照組" if is_static else "AI 動態組"
    print(f"📝 [{mode_str}] 成功寫入：{action} {shares} 股 {ticker} @ {price} 元。")
