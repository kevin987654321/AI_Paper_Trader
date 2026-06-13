import time
import os
import pandas as pd
from datetime import datetime
import config
from modules import fetcher, ml_brain, llm_brain, execution, notifier

def log_routine_check(ticker, price, status, is_static=False):
    """【系統巡邏日誌】區分宇宙寫入"""
    os.makedirs("data", exist_ok=True) 
    prefix = "[STATIC]" if is_static else "[DYNAMIC]"
    with open("data/patrol_log.txt", "a", encoding="utf-8") as f:
        now = datetime.now().strftime("%m/%d %H:%M")
        f.write(f"{prefix} [{now}] {ticker} @ {price:.1f} 元 -> {status}\n")

def get_ticker_ledger_status(ticker, is_static=False):
    """讀取【指定宇宙】的目前狀況與持股成本"""
    path = getattr(config, 'LEDGER_STATIC_PATH', "data/paper_ledger_static.csv") if is_static else config.LEDGER_PATH
    try:
        df = pd.read_csv(path)
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

def get_total_active_positions(is_static=False):
    """計算【指定宇宙】的總持倉數"""
    path = getattr(config, 'LEDGER_STATIC_PATH', "data/paper_ledger_static.csv") if is_static else config.LEDGER_PATH
    try:
        df = pd.read_csv(path)
        if len(df) == 0: return 0
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

def evaluate_strategy(ticker, current_price, df_data, ml_buy_signal, llm_signal, is_static):
    """核心：根據帶入的宇宙(is_static)，套用不同參數與決策"""
    # 決定要用哪一套參數
    sl_pct = getattr(config, 'STATIC_STOP_LOSS_PCT', 0.02) if is_static else config.STOP_LOSS_PCT
    tp_pct = getattr(config, 'STATIC_TAKE_PROFIT_PCT', 0.10) if is_static else config.TAKE_PROFIT_PCT
    risk_pct = getattr(config, 'STATIC_RISK_PER_TRADE', 0.02) if is_static else config.RISK_PER_TRADE
    
    current_cash, current_shares, avg_cost = get_ticker_ledger_status(ticker, is_static)
    total_active = get_total_active_positions(is_static)
    
    action_str = "繼續觀望"
    reason_str = "無"
    should_notify = False
    
    if current_shares > 0:
        # 💡 防吵機制：有股票才去檢查賣出訊號
        ml_sell_signal = ml_brain.check_sell_signal(df_data)
        
        take_profit_price = avg_cost * (1 + tp_pct)
        stop_loss_price = avg_cost * (1 - sl_pct)
        
        if current_price >= take_profit_price:
            action_str = "🎯 賣出停利"
            reason_str = f"觸發 {tp_pct*100}% 停利點 (成本 {avg_cost:.1f})"
            execution.log_trade("SELL", ticker, current_price, current_shares, is_static)
            should_notify = True
        elif current_price <= stop_loss_price:
            action_str = "🛡️ 賣出停損"
            reason_str = f"觸發 {sl_pct*100}% 停損點 (成本 {avg_cost:.1f})"
            execution.log_trade("SELL", ticker, current_price, current_shares, is_static)
            should_notify = True
        elif ml_sell_signal:
            action_str = "⚠️ 動能拔檔"
            reason_str = f"動能轉弱，提早出場 (成本 {avg_cost:.1f})"
            execution.log_trade("SELL", ticker, current_price, current_shares, is_static)
            should_notify = True
        else:
            action_str = "🤝 繼續抱牢"
            reason_str = f"防線 [{sl_pct*100}% / {tp_pct*100}%] 尚未觸發"
            should_notify = True 
            
    elif not ml_buy_signal:
        reason_str = "技術面無進場訊號"
        
    else:
        max_positions = getattr(config, 'MAX_POSITIONS', 3)
        if total_active >= max_positions:
            reason_str = f"達持倉上限 ({max_positions}檔)"
        elif not llm_signal:
            reason_str = "文官否決進場"
        else:
            max_loss_amount = current_cash * risk_pct
            shares_to_buy = int((max_loss_amount / sl_pct) / current_price)
            
            position_size_pct = getattr(config, 'POSITION_SIZE_PCT', 0.3)
            max_alloc_cash = current_cash * position_size_pct
            if (shares_to_buy * current_price) > max_alloc_cash:
                shares_to_buy = int(max_alloc_cash / current_price)
            
            if shares_to_buy > 0:
                action_str = "✅ 成功買進"
                reason_str = f"動態配置買入 {shares_to_buy} 股 (風控 {risk_pct*100}%)"
                execution.log_trade("BUY", ticker, current_price, shares_to_buy, is_static)
                should_notify = True
            else:
                reason_str = "可用現金不足分配"

    log_routine_check(ticker, current_price, f"{action_str} ({reason_str})", is_static)
    final_cash, final_shares, _ = get_ticker_ledger_status(ticker, is_static)
    
    return action_str, reason_str, should_notify, final_cash, final_shares

def run_trading_bot_for_ticker(ticker):
    """執行市場掃描，並同時結算雙宇宙的戰果"""
    print(f"\n 正在掃描標的: {ticker}...")
    
    df_data = fetcher.get_stock_data(ticker)
    if df_data is None or df_data.empty:
        print(f"⚠️ 無法抓取資料，跳過。")
        return 
        
    current_price = df_data['Close'].iloc[-1]
    df_data = ml_brain.calculate_indicators(df_data)
    ml_buy_signal = ml_brain.check_buy_signal(df_data)
    
    # 讀取技術面狀態供戰報使用
    latest_data = df_data.iloc[-1]
    current_rsi = latest_data.get('RSI_14', latest_data.get('RSI_21', 0))
    macd = latest_data.get('MACD_12_26_9', 0)
    macd_signal = latest_data.get('MACDs_12_26_9', 0)
    macd_status = "多頭" if macd > macd_signal else ("空頭" if macd < macd_signal else "平盤")

    # 如果有買進訊號，才呼叫文官 (省 API 額度)
    llm_signal = True
    if ml_buy_signal:
        print(f"📈 武官看好 {ticker}！呼叫文官(Gemini)進行二次確認...")
        real_news = fetcher.get_latest_news(ticker)
        llm_signal = llm_brain.analyze_sentiment(real_news)

    # 🌐 進入雙宇宙決策引擎
    dyn_action, dyn_reason, dyn_notify, dyn_cash, dyn_shares = evaluate_strategy(
        ticker, current_price, df_data, ml_buy_signal, llm_signal, is_static=False)
        
    sta_action, sta_reason, sta_notify, sta_cash, sta_shares = evaluate_strategy(
        ticker, current_price, df_data, ml_buy_signal, llm_signal, is_static=True)

    # 只要任何一個宇宙發生變化，就發送統整版 LINE 戰報
    if dyn_notify or sta_notify:
        tw_time = datetime.utcnow() + pd.Timedelta(hours=8)
        now_str = tw_time.strftime("%Y-%m-%d %H:%M")
        
        report_msg = f"""📊｜A/B 測試戰情報告
🕒｜{now_str}
▸ 標的：{ticker} @ {current_price:.1f}
▸ 指標：RSI {current_rsi:.1f} / {macd_status}
━━━━━━━━━━━━━━
【 🧠 AI 動態組 】
▸ 動作：{dyn_action}
▸ 說明：{dyn_reason}
▸ 現金：{dyn_cash:,.0f} 元 | 庫存：{dyn_shares} 股
------------------------------
【 ⚖️ 靜態對照組 】
▸ 動作：{sta_action}
▸ 說明：{sta_reason}
▸ 現金：{sta_cash:,.0f} 元 | 庫存：{sta_shares} 股
━━━━━━━━━━━━━━"""
        notifier.send_line_message(report_msg)
        print(f"✅ {ticker} 雙宇宙戰情報告已傳送至 LINE！")

def main_market_scan():
    execution.init_ledgers() 
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 啟動 A/B 測試雙引擎雷達掃描...")
    
    try:
        watchlist = getattr(config, 'WATCHLIST', [config.TICKER])
        for ticker in watchlist:
            run_trading_bot_for_ticker(ticker)
            time.sleep(2)
            
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 本次全市場掃描與下單判定完畢，系統安全結束。")
    except Exception as e:
        error_msg = f"⚠️ 系統運行發生嚴重錯誤: {e}"
        print(error_msg)
        notifier.send_line_message(error_msg)

if __name__ == "__main__":
    main_market_scan()
