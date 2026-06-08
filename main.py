import time
import os
import pandas as pd
from datetime import datetime, time as dt_time
import config
from modules import fetcher, ml_brain, llm_brain, execution

def is_market_open():
    """【今晚熬夜測試版】強制當作開盤中"""
    return True

def print_status_report():
    """戰情儀表板：讀取帳本並回報目前狀況"""
    os.system('cls' if os.name == 'nt' else 'clear') 
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print("==================================================")
    print(f"🤖 AI 交易系統持續運作中 | 系統時間: {now_str}")
    print("==================================================")
    
    if not os.path.exists(config.LEDGER_PATH):
        print("等待初始化帳本中...")
        return

    df = pd.read_csv(config.LEDGER_PATH)
    cash_left = df.iloc[-1]["Cash_Left"]
    
    buy_shares = df[df['Action'] == 'BUY']['Shares'].sum()
    sell_shares = df[df['Action'] == 'SELL']['Shares'].sum()
    current_shares = buy_shares - sell_shares
    
    print(f"💼 【目前資金水位】")
    print(f"  💵 剩餘現金： {cash_left:,.0f} 元")
    print(f"  📦 庫存股數： {current_shares} 股 ({config.TICKER})")
    
    market_status = "🟢 開盤中 (監控中...)" if is_market_open() else "🔴 收盤休眠中 (Zzz...)"
    print(f"\n📈 【市場狀態】: {market_status}")
    print("==================================================\n")

def run_trading_bot():
    """正式版交易邏輯"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在執行市場掃描...")
    
    # 1. 小弟抓取歷史數據與最新價格
    df_data = fetcher.get_stock_data(config.TICKER)
    if df_data is None:
        return
        
    current_price = df_data['Close'].iloc[-1]
    print(f"📊 取得 {config.TICKER} 最新價格: {current_price:.1f} 元")
    
    # 2. 武官計算指標
    df_data = ml_brain.calculate_indicators(df_data)
    ml_buy_signal = ml_brain.check_buy_signal(df_data)
    ml_sell_signal = ml_brain.check_sell_signal(df_data)
    
    # 讀取帳本，確認庫存與現金
    current_cash = execution.get_current_cash()
    df_ledger = pd.read_csv(config.LEDGER_PATH)
    buy_shares = df_ledger[df_ledger['Action'] == 'BUY']['Shares'].sum()
    sell_shares = df_ledger[df_ledger['Action'] == 'SELL']['Shares'].sum()
    current_shares = buy_shares - sell_shares
    
    # 3. 判斷進出場邏輯
    if ml_sell_signal and current_shares > 0:
        print(f"💰 觸發獲利了結！準備賣出 {current_shares} 股...")
        execution.log_trade("SELL", config.TICKER, current_price, current_shares)
        return
        
    if not ml_buy_signal:
        print("🛑 武官判定：目前無符合的進場條件，繼續觀望。\n")
        return
        
    print("📈 武官判定：出現技術面買進訊號！呼叫文官(Gemini)進行二次確認...")
    
    # 4. 文官判讀真實新聞
    print("📰 正在抓取最新財經新聞...")
    real_news = fetcher.get_latest_news(config.TICKER)
    
    llm_signal = llm_brain.analyze_sentiment(real_news)
    
    if not llm_signal:
        print("🛑 文官判定：偵測到市場負面情緒或總經風險，否決武官的買入決策。\n")
        return 
        
    print("🟢 文武雙全確認通過！準備下單...")
    
    # 5. 計算部位與執行紙上交易
    max_loss_amount = current_cash * config.RISK_PER_TRADE
    position_size = max_loss_amount / 0.05
    shares_to_buy = int(position_size / current_price)
    
    if shares_to_buy > 0 and (shares_to_buy * current_price) <= current_cash:
        execution.log_trade("BUY", config.TICKER, current_price, shares_to_buy)
        print("✅ 虛擬下單完成！\n")
    else:
        print("❌ 資金不足以承擔此次交易配置。\n")

def endless_loop():
    execution.init_ledger() 
    
    while True:
        try:
            print_status_report()
            
            if is_market_open():
                run_trading_bot()
                
                # 🛑 把這裡從 600 秒 (10分鐘) 改成 300 秒 (5分鐘)
                time.sleep(300) 
            else:
                # 收盤時：每 1 小時醒來檢查一次時間
                time.sleep(3600) 
                
        except Exception as e:
            print(f"⚠️ 系統發生例外錯誤: {e}")
            print("系統將在 60 秒後重新嘗試連線...")
            time.sleep(60)

if __name__ == "__main__":
    endless_loop()
