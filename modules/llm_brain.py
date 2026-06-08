import os
from datetime import datetime
import config

# 導入全新版本的 Google GenAI SDK
from google import genai

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