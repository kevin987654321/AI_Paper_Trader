import time
import os
import json
import pandas as pd
from datetime import datetime
import config
from modules import fetcher, ml_brain, llm_brain, execution, notifier

def get_group_params(group_id):
    """取得該宇宙的專屬參數 (若為 DYN 組且有 AI 設定檔，則覆寫)"""
    params = {
        "STA_1": {"risk": getattr(config, 'STA_1_RISK', 0.03), "atr_mult": getattr(config, 'STA_1_ATR', 3.0)},
        "STA_2": {"risk": getattr(config, 'STA_2_RISK', 0.02), "atr_mult": getattr(config, 'STA_2_ATR', 2.0)},
        "DYN_1": {"risk": getattr(config, 'DYN_1_RISK', 0.03), "atr_mult": getattr(config, 'DYN_1_ATR', 3.0)},
        "DYN_2": {"risk": getattr(config, 'DYN_2_RISK', 0.02), "atr_mult": getattr(config, 'DYN_2_ATR', 2.0)}
    }
    
    if group_id.startswith("DYN"):
        try:
            if os.path.exists("dynamic_config.json"):
                with open("dynamic_config.json", "r") as f:
                    dyn_data = json.load(f)
                    if group_id in dyn_data:
                        params[group_id]['risk'] = dyn_data[group_id].get('risk', params[group_id]['risk'])
                        params[group_id]['atr_mult'] = dyn_data[group_id].get('atr_mult', params[group_id]['atr_mult'])
        except Exception:
            pass
            
    return params[group_id]

def get_portfolio_breakdown(group_id):
    """計算 Core-Satellite 資金配置目前佔用額度"""
    path = execution.get_ledger_path(group_id)
    try:
        df = pd.read_csv(path)
        if len(df) == 0: return 0, 0, 0
        tech_count, def_count = 0, 0
        tickers = df[df['Ticker'] != 'NONE']['Ticker'].unique()
        for t in tickers:
            t_df = df[df['Ticker'] == t]
            shares = t_df[t_df['Action']=='BUY']['Shares'].sum() - t_df[t_df['Action']=='SELL']['Shares'].sum()
            if shares > 0:
                if t in getattr(config, 'TECH_TICKERS', []): tech_count += 1
                elif t in getattr(config, 'DEFENSIVE_TICKERS', []): def_count += 1
        return tech_count + def_count, tech_count, def_count
    except Exception:
        return 0, 0, 0

def get_ticker_ledger_status(ticker, group_id, df_data):
    """無狀態計算：讀取庫存，並利用歷史 K 線回推買進以來的最高價，用於計算 ATR 停損"""
    path = execution.get_ledger_path(group_id)
    try:
        df = pd.read_csv(path)
        if len(df) == 0: return 100000, 0, 0
        
        cash_left = df.iloc[-1]["Cash_Left"]
        ticker_df = df[df['Ticker'] == ticker]
        buy_shares = ticker_df[ticker_df['Action'] == 'BUY']['Shares'].sum()
        sell_shares = ticker_df[ticker_df['Action'] == 'SELL']['Shares'].sum()
        current_shares = buy_shares - sell_shares
        
        highest_price = 0
        if current_shares > 0:
            last_buy_record = ticker_df[ticker_df['Action'] == 'BUY'].iloc[-1]
            buy_date_str = last_buy_record['Date'].split(' ')[0] 
            buy_date = pd.to_datetime(buy_date_str).tz_localize(None)
            
            df_data_naive = df_data.copy()
            df_data_naive.index = df_data_naive.index.tz_localize(None)
            after_buy_data = df_data_naive[df_data_naive.index >= buy_date]
            
            if not after_buy_data.empty:
                highest_price = after_buy_data['Close'].max()
            else:
                highest_price = last_buy_record['Price']
                
        return cash_left, current_shares, highest_price
    except Exception:
        return 100000, 0, 0

def evaluate_strategy(ticker, df_data, ml_buy_signal, llm_signal, group_id):
    """進入特定宇宙，套用該宇宙的專屬戰略"""
    current_price = df_data['Close'].iloc[-1]
    curr_sma20 = df_data['SMA_20'].iloc[-1]
    curr_atr = df_data['ATRr_14'].iloc[-1]
    
    params = get_group_params(group_id)
    risk_pct = params['risk']
    atr_mult = params['atr_mult']
    
    cash, current_shares, highest_price = get_ticker_ledger_status(ticker, group_id, df_data)
    total_count, tech_count, def_count = get_portfolio_breakdown(group_id)
    
    action_str = "觀望"
    reason_str = "-"
    should_notify = False
    
    if current_shares > 0:
        # 動態計算最新防守線
        stop_price = highest_price - (curr_atr * atr_mult)
        
        if current_price <= stop_price:
            action_str = "🛡️ 停損出場"
            reason_str = f"跌破 ATR 防線 ({stop_price:.1f})"
            execution.log_trade("SELL", ticker, current_price, current_shares, group_id)
            should_notify = True
        elif current_price < curr_sma20 * 0.95:
            action_str = "⚠️ 破底逃命"
            reason_str = f"跌破月線 5% ({curr_sma20*0.95:.1f})"
            execution.log_trade("SELL", ticker, current_price, current_shares, group_id)
            should_notify = True
        else:
            action_str = "🤝 抱牢波段"
            reason_str = f"防線墊高至 {stop_price:.1f}"
            should_notify = True 
            
    elif not ml_buy_signal:
        reason_str = "無技術進場訊號"
        
    else:
        # Core-Satellite 額度檢查
        can_buy = False
        if ticker in getattr(config, 'TECH_TICKERS', []) and tech_count < 3:
            can_buy = True
        elif ticker in getattr(config, 'DEFENSIVE_TICKERS', []) and def_count < 2:
            can_buy = True
            
        if not can_buy:
            reason_str = "該類別持股達上限"
        elif not llm_signal:
            reason_str = "文官否決進場"
        else:
            # ATR 動態資金分配
            max_loss_amount = cash * risk_pct
            stop_distance = curr_atr * atr_mult
            shares_to_buy = int(max_loss_amount / stop_distance) if stop_distance > 0 else 0
            
            # 單檔上限 20%
            max_alloc = cash * 0.20
            if (shares_to_buy * current_price) > max_alloc:
                shares_to_buy = int(max_alloc / current_price)
                
            if shares_to_buy > 0:
                action_str = "✅ 成功買進"
                reason_str = f"ATR 動態配重 {shares_to_buy} 股"
                execution.log_trade("BUY", ticker, current_price, shares_to_buy, group_id)
                should_notify = True
            else:
                reason_str = "剩餘現金不足"

    final_cash, final_shares, _ = get_ticker_ledger_status(ticker, group_id, df_data)
    return action_str, reason_str, should_notify, final_cash, final_shares

def run_trading_bot_for_ticker(ticker):
    print(f"\n 正在掃描標的: {ticker}...")
    
    df_data = fetcher.get_stock_data(ticker)
    if df_data is None or df_data.empty:
        return 
        
    current_price = df_data['Close'].iloc[-1]
    df_data = ml_brain.calculate_indicators(df_data)
    ml_buy_signal = ml_brain.check_buy_signal(df_data)
    
    # 只要有買進訊號，呼叫文官審核一次即可，四個宇宙共用結果
    llm_signal = True
    if ml_buy_signal:
        print(f"📈 訊號亮起！呼叫文官進行大盤風險審查...")
        real_news = fetcher.get_latest_news(ticker)
        llm_signal = llm_brain.analyze_sentiment(real_news)

    # 🌐 平行進入四大宇宙執行策略
    groups = ["DYN_1", "DYN_2", "STA_1", "STA_2"]
    results = {}
    any_notify = False
    
    for g in groups:
        act, rsn, notif, cash, shares = evaluate_strategy(ticker, df_data, ml_buy_signal, llm_signal, g)
        results[g] = {"act": act, "rsn": rsn, "cash": cash, "shares": shares}
        if notif: any_notify = True

    # 只要有任何一個宇宙發生變化或抱倉，就發送一份統整戰報
    if any_notify:
        tw_time = datetime.utcnow() + pd.Timedelta(hours=8)
        now_str = tw_time.strftime("%Y-%m-%d %H:%M")
        
        report_msg = f"""📊｜4D 矩陣戰情報告
🕒｜{now_str}
▸ 標的：{ticker} @ {current_price:.1f}
━━━━━━━━━━━━━━
【 🚀 DYN-1 AI 積極動態 】
▸ {results['DYN_1']['act']} ({results['DYN_1']['shares']} 股)
▸ {results['DYN_1']['rsn']}
------------------------------
【 🛡️ DYN-2 AI 穩健動態 】
▸ {results['DYN_2']['act']} ({results['DYN_2']['shares']} 股)
▸ {results['DYN_2']['rsn']}
------------------------------
【 ⚔️ STA-1 靜態積極對照 】
▸ {results['STA_1']['act']} ({results['STA_1']['shares']} 股)
▸ {results['STA_1']['rsn']}
------------------------------
【 🧱 STA-2 靜態穩健對照 】
▸ {results['STA_2']['act']} ({results['STA_2']['shares']} 股)
▸ {results['STA_2']['rsn']}
━━━━━━━━━━━━━━"""
        notifier.send_line_message(report_msg)
        print(f"✅ {ticker} 4D 戰情報告已傳送至 LINE！")

def main_market_scan():
    execution.init_ledgers() 
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 啟動 4D 平行宇宙矩陣雷達...")
    
    try:
        watchlist = getattr(config, 'WATCHLIST', [])
        for ticker in watchlist:
            run_trading_bot_for_ticker(ticker)
            time.sleep(2)
            
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 本次全市場矩陣掃描完畢。")
    except Exception as e:
        error_msg = f"⚠️ 系統運行發生嚴重錯誤: {e}"
        print(error_msg)
        notifier.send_line_message(error_msg)

if __name__ == "__main__":
    main_market_scan()
