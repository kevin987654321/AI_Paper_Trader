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

def get_ticker_ledger_status(ticker):
    """讀取並計算【特定股票】的目前狀況與持股成本"""
    try:
        df = pd.read_csv(config.LEDGER_PATH)
        if len(df) == 0:
            return config.INITIAL_CAPITAL, 0, 0
        
        cash_left = df.iloc[-1]["Cash_Left"]
        
        ticker_df = df[df['Ticker'] == ticker]
        buy_shares = ticker_df[ticker_df['Action'] == 'BUY']['Shares'].sum()
        sell_shares = ticker_df[ticker_df['Action'] == 'SELL']['Shares'].sum()
        current_shares = buy_shares - sell_shares
        
        avg_cost = 0
        if current_shares > 0:
            buy_records = ticker_df[ticker_df['Action'] == 'BUY']
            if not buy_records.empty:
                avg_cost = buy_records.iloc[-1]['Price']
                
        return cash_left, current_shares, avg_cost
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return config.INITIAL_CAPITAL, 0, 0

def get_total_active_positions():
    """計算目前整個帳戶總共持有了幾檔不同的股票部位"""
    try:
        df = pd.read_csv(config.LEDGER_PATH)
        if len(df) == 0:
            return 0
        
        all_tickers = df[df['Ticker'] != 'NONE']['Ticker'].unique()
        active_count = 0
        
        for ticker in all_tickers:
            ticker_df = df[df['Ticker'] == ticker]
            buy_shares = ticker_df[ticker_df['Action'] == 'BUY']['Shares'].sum()
            sell_shares = ticker_df[ticker_df['Action'] == 'SELL']['Shares'].sum()
            if (buy_shares - sell_shares) > 0:
                active_count += 1
        return active_count
    except Exception:
        return 0

def run_trading_bot_for_ticker(ticker, total_active_positions):
    """針對單一股票執行技術分析與交易決策"""
    print(f" 正在掃描標的: {ticker}...")
    
    # 1. 抓取最新價格
    df_data = fetcher.get_stock_data(ticker)
    if df_data is None or df_data.empty:
        print(f"⚠️ 無法抓取到 {ticker} 的歷史價格資料，跳過。")
        return 
        
    current_price = df_data['Close'].iloc[-1]
    
    # 2. 武官計算指標
    df_data = ml_brain.calculate_indicators(df_data)
    
    # 💡 核心修正：一開始【只檢查買進訊號】，不檢查賣出！這樣就不會亂印死亡交叉警告了
    ml_buy_signal = ml_brain.check_buy_signal(df_data)
    
    latest_data = df_data.iloc[-1]
    current_rsi = latest_data.get('RSI_14', latest_data.get('RSI_21', 0))
    macd = latest_data.get('MACD_12_26_9', 0)
    macd_signal = latest_data.get('MACDs_12_26_9', 0)
    
    if macd > macd_signal:
        macd_status = "多頭 (快線在上)"
    elif macd < macd_signal:
        macd_status = "空頭 (快線在下)"
    else:
        macd_status = "平盤交纏"

    current_cash, current_shares, avg_cost = get_ticker_ledger_status(ticker)
    
    action_str = "繼續觀望"
    reason_str = "無"
    should_notify = False 
    
    # 3. 判斷進出場邏輯
    if current_shares > 0:
        # 💡 核心修正：只有在確定手上有庫存時，才叫武官檢查是不是該賣了！
        ml_sell_signal = ml_brain.check_sell_signal(df_data)
        
        take_profit_price = avg_cost * (1 + config.TAKE_PROFIT_PCT)
        stop_loss_price = avg_cost * (1 - config.STOP_LOSS_PCT)
        
        if current_price >= take_profit_price:
            action_str = "🎯 賣出停利"
            reason_str = f"觸發 {config.TAKE_PROFIT_PCT*100}% 停利點 (成本 {avg_cost:.1f})"
            execution.log_trade("SELL", ticker, current_price, current_shares)
            should_notify = True
        elif current_price <= stop_loss_price:
            action_str = "🛡️ 賣出停損"
            reason_str = f"觸發 {config.STOP_LOSS_PCT*100}% 停損點 (成本 {avg_cost:.1f})"
            execution.log_trade("SELL", ticker, current_price, current_shares)
            should_notify = True
        elif ml_sell_signal:
            action_str = "⚠️ 動能轉弱賣出"
            reason_str = f"MACD 死亡交叉，提早拔檔 (成本 {avg_cost:.1f})"
            execution.log_trade("SELL", ticker, current_price, current_shares)
            should_notify = True
        else:
            action_str = "🤝 繼續抱牢"
            reason_str = f"尚未觸發停損/停利 (目前成本: {avg_cost:.1f})"
            should_notify = True 
            
    elif not ml_buy_signal:
        reason_str = "武官判定：技術面無進場訊號"
        
    else:
        max_positions = getattr(config, 'MAX_POSITIONS', 3)
        if total_active_positions >= max_positions:
            reason_str = f"武官看好，但目前持部位數已達上限 ({max_positions}檔)，放棄進場以控管風險"
        else:
            print(f"📈 武官看好 {ticker}！呼叫文官(Gemini)進行二次確認...")
            real_news = fetcher.get_latest_news(ticker)
            llm_signal = llm_brain.analyze_sentiment(real_news)
            
            if not llm_signal:
                reason_str = "文官否決：偵測到市場負面情緒或總經風險"
            else:
                max_loss_amount = current_cash * config.RISK_PER_TRADE
                shares_to_buy = int((max_loss_amount / config.STOP_LOSS_PCT) / current_price)
                
                position_size_pct = getattr(config, 'POSITION_SIZE_PCT', 0.3)
                max_alloc_cash = current_cash * position_size_pct
                if (shares_to_buy * current_price) > max_alloc_cash:
                    shares_to_buy = int(max_alloc_cash / current_price)
                
                if shares_to_buy > 0:
                    action_str = "✅ 成功買進"
                    reason_str = f"確認訊號！動態控管買入 {shares_to_buy} 股"
                    execution.log_trade("BUY", ticker, current_price, shares_to_buy)
                    should_notify = True
                else:
                    reason_str = "買進訊號確認，但剩餘可用現金不足"

    # 4. 寫入日誌
    log_routine_check(ticker, current_price, f"{action_str} ({reason_str})")
    
    # 5. LINE 通知發送邏輯
    if should_notify:
        final_cash, final_shares, _ = get_ticker_ledger_status(ticker)
        tw_time = datetime.utcnow() + pd.Timedelta(hours=8)
        now_str = tw_time.strftime("%Y-%m-%d %H:%M")
        
        report_msg = f"""📊｜AI 交易戰情報告
🕒｜{now_str}
━━━━━━━━━━━━━━
【 📈 市場報價 】
 ▸ 標的：{ticker}
 ▸ 股價：{current_price:.1f} 元
------------------------------
【 🎛️ 武官儀表板 】
 ▸ ＲＳＩ：{current_rsi:.1f}
 ▸ 動能：{macd_status}
------------------------------
【 📋 系統決策 】
 ▸ 動作：{action_str}
 ▸ 說明：{reason_str}
------------------------------
【 💼 帳戶概況 】
 ▸ 全局現金：{final_cash:,.0f} 元
 ▸ 當前庫存：{final_shares} 股
━━━━━━━━━━━━━━"""
        notifier.send_line_message(report_msg)
        print(f"✅ {ticker} 戰情報告已成功傳送至 LINE！")

def main_market_scan():
    """全市場雷達掃描模式的主入口"""
    execution.init_ledger() 
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 啟動多重標的雷達掃描與資金控管系統...")
    
    try:
        total_active_positions = get_total_active_positions()
        print(f"💼 目前帳戶已持有總部位數: {total_active_positions} 檔")
        
        watchlist = getattr(config, 'WATCHLIST', [config.TICKER])
        
        for ticker in watchlist:
            run_trading_bot_for_ticker(ticker, total_active_positions)
            total_active_positions = get_total_active_positions()
            time.sleep(2)
            
            from modules import github_sync
            github_sync.push_to_github("🤖 巡邏完畢：更新最新帳本")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 本次全市場掃描與下單判定完畢，系統安全結束。")
    except Exception as e:
        error_msg = f"⚠️ 系統運行發生嚴重錯誤: {e}"
        print(error_msg)
        notifier.send_line_message(error_msg)

if __name__ == "__main__":
    main_market_scan()
