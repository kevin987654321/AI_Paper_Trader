import os
import pandas as pd
from datetime import datetime
import config
import google.generativeai as genai

# 初始化 Gemini 模型
genai.configure(api_key=config.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-3.5-flash')

def log_gemini_analysis(news_text, analysis_result, final_decision):
    """將 Gemini 的分析過程記錄到日誌檔中"""
    log_path = "data/gemini_analysis_log.txt"
    os.makedirs("data", exist_ok=True)
        
    with open(log_path, "a", encoding="utf-8") as f:
        f.write("==================================================\n")
        f.write(f"🕒 分析時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"📰 處理新聞片段:\n{news_text[:200]}... (節錄)\n") 
        f.write("--------------------------------------------------\n")
        f.write(f"🧠 Gemini 分析報告:\n{analysis_result}\n")
        f.write("--------------------------------------------------\n")
        f.write(f"⚖️ 最終決策: {'✅ 放行 (TRUE)' if final_decision else '🚨 否決 (FALSE)'}\n")
        f.write("==================================================\n\n")

def analyze_sentiment(news_text):
    """呼叫 Gemini 判讀新聞情緒，作為大盤風險最後一道防線"""
    if not news_text:
        return True 
        
    prompt = f"""
    你是一位華爾街的量化風險控管專家。
    請分析以下關於這檔股票的最新新聞：
    {news_text}
    
    請問這些新聞中，是否包含「極度致命的利空」（例如：假帳、工廠大火、高層被捕、掉大單）？
    如果只是普通的營收衰退、外資降評、股價波動，請視為正常市場雜訊。
    
    請先給出簡短的分析理由（50字內），最後在獨立的一行只輸出 "TRUE" (代表安全，可以買進) 或 "FALSE" (代表極度危險，禁止買進)。
    """
    try:
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        final_decision = "TRUE" in result_text.upper()
        log_gemini_analysis(news_text, result_text, final_decision)
        return final_decision
    except Exception as e:
        print(f"⚠️ Gemini API 發生錯誤: {e}")
        return True # 若 API 壞掉，預設不阻擋武官交易

def generate_daily_summary():
    """盤後產生 4D 矩陣總結報告 (給 daily_report.py 呼叫)"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # 讀取 4 個平行宇宙的最新狀態與今日交易
    ledger_summary = ""
    groups = {
        "🚀 DYN_1 (AI 積極)": getattr(config, 'LEDGER_DYN_1', "data/ledger_dyn_1_agg.csv"),
        "🛡️ DYN_2 (AI 穩健)": getattr(config, 'LEDGER_DYN_2', "data/ledger_dyn_2_con.csv"),
        "⚔️ STA_1 (靜態積極)": getattr(config, 'LEDGER_STA_1', "data/ledger_sta_1_agg.csv"),
        "🧱 STA_2 (靜態穩健)": getattr(config, 'LEDGER_STA_2', "data/ledger_sta_2_con.csv")
    }
    
    for name, path in groups.items():
        try:
            df = pd.read_csv(path)
            if not df.empty:
                cash = df.iloc[-1]["Cash_Left"]
                profit = cash - getattr(config, 'INITIAL_CAPITAL', 100000)
                
                # 抓出今天的交易紀錄
                today_trades = df[df['Date'].str.contains(today_str)]
                trade_count = len(today_trades)
                
                ledger_summary += f"【{name}】 總資產: {cash:,.0f} (淨利 {profit:,.0f}) | 今日交易筆數: {trade_count}\n"
                if trade_count > 0:
                    for _, row in today_trades.iterrows():
                        ledger_summary += f"  - {row['Action']} {row['Shares']}股 {row['Ticker']} @ {row['Price']}元\n"
        except Exception:
            ledger_summary += f"【{name}】 尚未建立或讀取失敗\n"

    # 組裝給 Gemini 的 Prompt
    prompt = f"""
    你是一位頂級的避險基金經理人。現在台股已經收盤，你的 4 支量化交易機器人跑出了以下成績。
    請根據「4D 平行宇宙戰果」，寫一份大約 150~200 字的【台股收盤總結報告】給老闆。

    【今日 4D 宇宙戰果】
    {ledger_summary}

    請嚴格遵守以下輸出模板（直接輸出文字，絕對不要加上 Markdown 的 ``` 符號）：

    📝｜AI 基金經理人收盤總結
    📅｜日期：{today_str}
    ━━━━━━━━━━━━━━
    【 🎯 今日矩陣操作回顧 】
    (請判讀上方數據，用專業口吻總結今天這四組有沒有進行買賣。例如：今日市場震盪，AI 積極組率先觸發停損，但穩健組成功避開風險，雙方展現不同調性...等)

    【 💰 宇宙淨值戰況 】
    (列出各組目前的獲利狀況，並做一句精闢的點評，例如：目前由 STA_1 靜態積極組暫居獲利王寶座)
    ━━━━━━━━━━━━━━
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"⚠️ 產生報告失敗: {e}"
