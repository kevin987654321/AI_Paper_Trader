import os
from datetime import datetime
import config

# 導入全新版本的 Google GenAI SDK
import google.generativeai as genai

def log_gemini_analysis(news_text, analysis_result, final_decision):
    """
    將 Gemini 的分析過程記錄到日誌檔中
    """
    log_path = "data/gemini_analysis_log.txt"
    
    # 確保 data 資料夾存在
    if not os.path.exists("data"):
        os.makedirs("data")
        
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
    """
    呼叫 Gemini 判讀新聞情緒，並產生詳細分析報告
    """
    if not news_text or len(news_text) < 10:
        return True

    try:
        # 使用新版 Client 的寫法
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        
        prompt = f"""
        你現在是一位華爾街頂級的風險控管專家。
        請閱讀以下關於【{config.TICKER}】或大盤的財經新聞：
        
        {news_text}
        
        任務 1：請用繁體中文，簡短分析這則新聞是否包含「系統性崩盤」、「黑天鵝事件」或「毀滅性打擊（如假帳、破產、產線全毀）」。(字數限制：100字以內)
        任務 2：基於上述分析，如果你認為發生了毀滅性風險，請在報告的最後一行獨立寫上：【判定結果：FALSE】。如果你認為沒有毀滅性風險，請在最後一行獨立寫上：【判定結果：TRUE】。
        """
        
        # 更換為最新的 gemini-2.5-flash 模型並使用新版生成指令
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        analysis_text = response.text.strip()
        
        # 解析最後一行，抓取最終判定
        if "判定結果：FALSE" in analysis_text:
            final_decision = False
            print("🚨 [文官警告] Gemini 偵測到重大市場風險，已將分析報告寫入日誌！")
        else:
            final_decision = True
            print("✅ [文官放行] Gemini 判定目前無重大系統性風險，分析報告已記錄。")
            
        # 將過程寫入日誌檔
        log_gemini_analysis(news_text, analysis_text, final_decision)
            
        return final_decision
            
    except Exception as e:
        print(f"⚠️ 呼叫 Gemini API 時發生錯誤: {e}")
        return False

def generate_daily_report():
    """讀取今日日誌與帳本，讓 Gemini 產生收盤總結報告"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "⚠️ 找不到 Gemini API Key，無法產生報告"

    genai.configure(api_key=api_key)
    # 使用 1.5-flash 模型，速度快且便宜
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # 取得今天日期的字串 (例如 "06/09")，用來過濾日誌
    today_str = datetime.now().strftime("%m/%d")
    
    # 1. 讀取巡邏日誌 (只抓今天的紀錄)
    patrol_logs = ""
    try:
        with open("data/patrol_log.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
            today_lines = [line for line in lines if today_str in line]
            patrol_logs = "".join(today_lines)
    except Exception:
        patrol_logs = "無今日巡邏紀錄"

    # 2. 讀取帳本
    ledger_logs = ""
    try:
        with open("data/paper_ledger.csv", "r", encoding="utf-8") as f:
            ledger_logs = f.read()
    except Exception:
        ledger_logs = "無帳本紀錄"

    # 3. 組合給 Gemini 的 Prompt 模板
    prompt = f"""
    你是一位專業的 AI 股票交易員。現在台股已經收盤，請根據以下的「今日巡邏日誌」與「歷史帳本」，
    寫一份大約 150 字的【台股收盤總結報告】。

    【今日巡邏日誌】
    {patrol_logs}

    【歷史帳本】
    {ledger_logs}

    請嚴格遵守以下輸出模板（直接輸出文字，絕對不要加上 Markdown 的 ``` 符號）：

    📝｜AI 交易員收盤總結
    📅｜日期：(填入今日日期)
    ━━━━━━━━━━━━━━
    【 🎯 今日操作回顧 】
    (請判讀日誌，用生動、專業的口吻總結今天有沒有買賣，以及主要的原因。例如：今日大盤震盪，雖然武官持續監控，但動能未達買進標準，故全日維持空手觀望。)

    【 💰 帳戶最終狀態 】
    (請判讀帳本，列出目前最新現金結餘與庫存股數)

    【 🔮 明日展望 】
    (請根據今日的技術面狀態，給出一句簡短的明日策略預告，例如：明日若持續下探將關注 RSI 是否落入超賣區。)
    ━━━━━━━━━━━━━━
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"⚠️ 收盤報告生成失敗：{e}"
