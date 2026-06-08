import time
import os
import pandas as pd
from datetime import datetime, time as dt_time
import config
from modules import fetcher, ml_brain, llm_brain, execution

def log_routine_check(ticker, price, status):
    """【系統巡邏日誌】不管有沒有買賣，都留下一行極簡紀錄"""
    os.makedirs("data", exist_ok=True) # 確保 data 資料夾存在
    with open("data/patrol_log.txt", "a", encoding="utf-8") as f:
        now = datetime.now().strftime("%m/%d %H:%M")
        f.write(f"[{now}] {ticker} @ {price:.1f} 元 -> {status}\n")

def print_status_report():
    """戰情儀表板：讀取帳本並印出目前狀況 (移除清空終端機指令)"""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print("==================================================")
    print(f"🤖 AI 單次排程交易系統 | 系統時間: {now_str}")
    print("==================================================")
    
    if not os.path.exists(config.LEDGER_PATH):
        print("等待初始化帳本中...")
        return

    try:
        df = pd.read_csv(config.LEDGER_PATH)
        if len(df) == 0:
             print("帳本為空，目前尚未有交易紀錄。")
        else:
            cash_left = df.iloc[-1]["Cash_Left"]
            buy_shares = df[df['Action'] == 'BUY']['Shares'].sum()
            sell_shares = df[df['Action'] == 'SELL']['Shares'].sum()
            current_shares = buy_shares - sell_shares
            
            print(f"💼 【目前資金水位】")
            print(f"  💵 剩餘現金： {cash_left:,.0f} 元")
            print(f"  📦 庫存股數： {current_shares} 股 ({config.TICKER})")
    except Exception as e:
        print(f"讀取帳本失敗: {e}")

    print("==================================================\n")

def run_trading_bot():
    """正式版交易邏輯"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在執行市場掃描...")
    
    # 1. 小弟抓取歷史數據與最新價格
    df_data = fetcher.get_stock_data(config.TICKER)
    if df_data is None:
        return # 如果抓不到資料就跳過這次，不強行寫入日誌
        
    current_price = df_data['Close'].iloc[-1]
    print(f"📊 取得 {config.TICKER} 最新價格: {current_price:.1f} 元")
    
    # 2. 武官計算指標
    df_data = ml_brain.calculate_indicators(df_data)
    ml_buy_signal = ml_brain.check_buy_signal(df_data)
    ml_sell_signal = ml_brain.check_sell_signal(df_data)
    
    # 讀取帳本，確認庫存與現金
    current_cash = execution.get_current_cash()
    
    # 計算目前庫存
    try:
        df_ledger = pd.read_csv(config.LEDGER_PATH)
        buy_shares = df_ledger[df_ledger['Action'] == 'BUY']['Shares'].sum()
        sell_shares = df_ledger[df_ledger['Action'] == 'SELL']['Shares'].sum()
        current_shares = buy_shares - sell_shares
    except (FileNotFoundError, pd.errors.EmptyDataError):
        current_shares = 0
    
    # 3. 判斷進出場邏輯
    if ml_sell_signal and current_shares > 0:
        print(f"💰 觸發獲利了結！準備賣出 {current_shares} 股...")
        execution.log_trade("SELL", config.TICKER, current_price, current_shares)
        log_routine_check(config.TICKER, current_price, "🟢 觸發賣出停利！")
        return
        
    if not ml_buy_signal:
        print("🛑 武官判定：目前無符合的進場條件，繼續觀望。\n")
        log_routine_check(config.TICKER, current_price, "👀 條件不符，繼續觀望")
        return
        
    print("📈 武官判定：出現技術面買進訊號！呼叫文官(Gemini)進行二次確認...")
    
    # 4. 文官判讀真實新聞
    print("📰 正在抓取最新財經新聞...")
    real_news = fetcher.get_latest_news(config.TICKER)
    
    llm_signal = llm_brain.analyze_sentiment(real_news)
    
    if not llm_signal:
        print("🛑 文官判定：偵測到市場負面情緒或總經風險，否決武官的買入決策。\n")
        log_routine_check(config.TICKER, current_price, "🛑 武官想買，但遭文官否決")
        return 
        
    print("🟢 文武雙全確認通過！準備下單...")
    
    # 5. 計算部位與執行紙上交易
    max_loss_amount = current_cash * config.RISK_PER_TRADE
    position_size = max_loss_amount / 0.05
    shares_to_buy = int(position_size / current_price)
    
    if shares_to_buy > 0 and (shares_to_buy * current_price) <= current_cash:
        execution.log_trade("BUY", config.TICKER, current_price, shares_to_buy)
        print("✅ 虛擬下單完成！\n")
        log_routine_check(config.TICKER, current_price, "✅ 文武雙全，成功買進！")
    else:
        print("❌ 資金不足以承擔此次交易配置。\n")
        log_routine_check(config.TICKER, current_price, "❌ 買進訊號確認，但資金不足")


def main_single_run():
    """單次執行模式的入口 (給 GitHub Actions 呼叫用)"""
    # 1. 確保帳本存在
    execution.init_ledger() 
    
    # 2. 開盤對時邏輯 (等待到真正的 09:00 才繼續往下走)
    print("等待台股開盤 (09:00)...")
    while True:
        # 注意：我們使用 utcnow + 8 小時來強制換算成台灣時間，避免伺服器時區問題
        tw_time = datetime.utcnow() + pd.Timedelta(hours=8) 
        tw_time_str = tw_time.strftime("%H:%M")
        
        if tw_time_str >= "09:00":
            break
        print(f"目前台灣時間 {tw_time_str}，稍候 30 秒...")
        time.sleep(30)
    
    print("✅ 09:00 開盤啦！正式啟動交易邏輯。")
    
    # 3. 執行印出狀態與主程式
    try:
        print_status_report()
        run_trading_bot()
        print("✅ 今日排程執行完畢，系統安全結束。")
    except Exception as e:
        print(f"⚠️ 系統發生例外錯誤: {e}")


if __name__ == "__main__":
    # 原本是呼叫 endless_loop()，現在改為單次執行的 main_single_run()
    main_single_run()
