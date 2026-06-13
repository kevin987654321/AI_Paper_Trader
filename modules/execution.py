import pandas as pd
import os
import config
from datetime import datetime

def get_ledger_path(group_id):
    """根據群組代號回傳對應的帳本路徑"""
    paths = {
        "DYN_1": getattr(config, 'LEDGER_DYN_1', "data/ledger_dyn_1.csv"),
        "DYN_2": getattr(config, 'LEDGER_DYN_2', "data/ledger_dyn_2.csv"),
        "STA_1": getattr(config, 'LEDGER_STA_1', "data/ledger_sta_1.csv"),
        "STA_2": getattr(config, 'LEDGER_STA_2', "data/ledger_sta_2.csv")
    }
    return paths.get(group_id)

def init_ledgers():
    """一次初始化 4 個平行宇宙的帳本"""
    os.makedirs("data", exist_ok=True)
    groups = ["DYN_1", "DYN_2", "STA_1", "STA_2"]
    
    for g in groups:
        path = get_ledger_path(g)
        if not os.path.exists(path) or os.stat(path).st_size == 0:
            df = pd.DataFrame(columns=["Date", "Action", "Ticker", "Price", "Shares", "Total_Value", "Cash_Left"])
            df.loc[0] = [datetime.now().strftime("%Y-%m-%d %H:%M"), "DEPOSIT", "NONE", 0, 0, config.INITIAL_CAPITAL, config.INITIAL_CAPITAL]
            df.to_csv(path, index=False)
            print(f"✅ [{g}] 虛擬帳本初始化完成。")

def get_current_cash(group_id):
    path = get_ledger_path(group_id)
    df = pd.read_csv(path)
    return df.iloc[-1]["Cash_Left"]

def log_trade(action, ticker, price, shares, group_id):
    """將交易精準寫入指定的平行宇宙帳本"""
    path = get_ledger_path(group_id)
    df = pd.read_csv(path)
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
    df.to_csv(path, index=False)
    print(f"📝 [{group_id}] 成功寫入：{action} {shares} 股 {ticker} @ {price} 元。")
