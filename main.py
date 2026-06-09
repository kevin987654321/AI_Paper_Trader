import time
import os
import pandas as pd
from datetime import datetime
import config
from modules import fetcher, ml_brain, llm_brain, execution, notifier

def log_routine_check(ticker, price, status):
    """【系統巡邏日誌】不管有沒有買賣，都留下一行極簡紀錄"""
    os.makedirs("data", exist_ok=True) 
    with open("data/patrol_log.txt", "a", encoding="utf-8") as f:
        now = datetime.now().strftime("%m/%d %H:%M")
        f.write(f"[{now}] {ticker} @ {price:.1f} 元 -> {status}\n")

def get_ledger_status():
    """讀取並計算帳戶目前狀況"""
    try:
        df = pd.read_csv(config.LEDGER_PATH)
        if len(df) == 0:
            return 100000, 0 # 假設初始本金 10 萬
        cash_left = df.iloc[-1]["Cash_Left"]
        buy_shares = df[df['Action'] == 'BUY']['Shares'].sum()
        sell_shares = df[df['Action'] == 'SELL']['Shares'].sum()
        return cash_left, buy_shares - sell_shares
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return 100000, 0

def run_trading_bot():
    """正式版交易邏輯"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在執行市場掃描...")
    
    # 1. 抓取最新價格
    df_data = fetcher.get_stock_data(config.TICKER)
    if df_data is None:
        notifier.send_line_message("[ 系統異常 ]\n無法抓取到歷史價格資料，已暫停運作。")
        return 
        
    current_price = df_data['Close'].iloc[-1]
    
    # 2. 武官計算指標
    df_data = ml_brain.calculate_indicators(df_data)
    ml_buy_signal = ml_brain.check_buy_signal(df_data)
    ml_sell_signal = ml_brain.check_sell_signal(df_data)
    
    current_cash, current_shares = get_ledger_status()
    
    # 預設變數 (移除 emoji，改為專業字眼)
    action_str = "繼續觀望"
    reason_str = "無"
    
    # 3. 判斷進出場邏輯
    if ml_sell_signal and current_shares > 0:
        action_str = "賣出停利"
        reason_str = "武官判斷：觸發技術面獲利了結條件"
        execution.log_trade("SELL", config.TICKER, current_price, current_shares)
        
    elif not ml_buy_signal:
        reason_str = "武官判定：技術面無進場訊號"
        
    else:
        print("📈 武官看好！呼叫文官(Gemini)進行二次確認...")
        real_news = fetcher.get_latest_news(config.TICKER)
        llm_signal = llm_brain.analyze_sentiment(real_news)
        
        if not llm_signal:
            reason_str = "文官否決：偵測到市場負面情緒或總經風險"
        else:
            max_loss_amount = current_cash * config.RISK_PER_TRADE
            shares_to_buy = int((max_loss_amount / 0.05) / current_price)
            
            if shares_to_buy > 0 and (shares_to_buy * current_price) <= current_cash:
                action_str = "成功買進"
                reason_str = "文武雙全，確認買進訊號並執行虛擬下單"
                execution.log_trade("BUY", config.TICKER, current_price, shares_to_buy)
            else:
                reason_str = "買進訊號確認，但現金不足以承擔此次交易"

    # 4. 交易結束後，寫入日誌並抓取最新餘額
    log_routine_check(config.TICKER, current_price, f"{action_str} ({reason_str})")
    final_cash, final_shares = get_ledger_status()
    
    # 5. 組合排版精美的 LINE 訊息並發送
    tw_time = datetime.utcnow() + pd.Timedelta(hours=8)
    now_str = tw_time.strftime("%Y-%m-%d %H:%M")
    
    # 💡 利用全形框線與縮排，建立明確的區塊感 (請直接完整複製這段 f-string)
    report_msg = f"""📊｜AI 交易戰情報告
🕒｜{now_str}
━━━━━━━━━━━━━━
【 📈 市場報價 】
 ▸ 標的：{config.TICKER}
 ▸ 股價：{current_price:.1f} 元
------------------------------
【 📋 系統決策 】
 ▸ 動作：{action_str}
 ▸ 說明：{reason_str}
------------------------------
【 💼 帳戶概況 】
 ▸ 現金：{final_cash:,.0f} 元
 ▸ 庫存：{final_shares} 股
━━━━━━━━━━━━━━"""
    
    notifier.send_line_message(report_msg)
    print("✅ 戰情報告已傳送至 LINE！")

def main_single_run():
    """單次執行模式的入口 (排程精準呼叫，不需死等)"""
    execution.init_ledger() 
    print("啟動交易邏輯...")
    
    try:
        run_trading_bot()
        print("✅ 本次排程執行完畢，系統安全結束。")
    except Exception as e:
        error_msg = f"⚠️ 系統發生嚴重錯誤: {e}"
        print(error_msg)
        notifier.send_line_message(error_msg)

if __name__ == "__main__":
    main_single_run()
