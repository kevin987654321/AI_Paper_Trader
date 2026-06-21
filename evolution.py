import pandas as pd
from google import genai
import json
import os
import re
from datetime import datetime
import config

def analyze_ledger():
    """讀取帳本，計算基礎績效指標，準備餵給 Gemini"""
    if not os.path.exists(config.LEDGER_PATH):
        return None

    try:
        df = pd.read_csv(config.LEDGER_PATH)
        sell_records = df[df['Action'] == 'SELL']

        if len(sell_records) == 0:
            return "目前還沒有賣出紀錄（皆為持倉或空手），無法計算實際損益勝率。"

        # 計算目前的投資報酬率 (ROI)
        initial_cash = config.INITIAL_CAPITAL
        current_cash = df.iloc[-1]['Cash_Left']
        roi = ((current_cash - initial_cash) / initial_cash) * 100
        
        total_trades = len(sell_records)
        
        # 簡單的績效摘要
        report = f"""
        - 初始資金: {initial_cash:,.0f} 元
        - 目前現金: {current_cash:,.0f} 元
        - 總報酬率 (ROI): {roi:.2f}%
        - 總共完成交易: {total_trades} 筆 (包含停損、停利與動能轉弱賣出)
        """
        return report
        
    except Exception as e:
        print(f"分析帳本失敗: {e}")
        return None

def run_evolution():
    """呼叫 Gemini 進行反思，並輸出新參數"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🧬 啟動系統自我進化與反思機制...")
    
    performance_data = analyze_ledger()
    if not performance_data or "無法計算" in performance_data:
        print("⚠️ 交易樣本不足，AI 決定本週維持原設定，暫不進化。")
        return

    # 設定 Gemini 金鑰
    client = genai.Client(api_key=config.GEMINI_API_KEY)

    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents=prompt
    )

    # 建立系統提示詞 (Prompt)
    prompt = f"""
    你現在是一位頂尖的量化交易策略大師。
    我們的交易系統目前使用以下參數：
    - 停損比例 (STOP_LOSS_PCT): {config.STOP_LOSS_PCT}
    - 停利比例 (TAKE_PROFIT_PCT): {config.TAKE_PROFIT_PCT}
    - 單筆資金風險比例 (RISK_PER_TRADE): {config.RISK_PER_TRADE}

    近期的真實交易績效結算如下：
    {performance_data}

    任務：
    請根據上述的「總報酬率」判斷是否需要微調參數。
    - 如果嚴重虧損：代表停損可能太寬（賠太多）或停利太難達到，請建議縮小數值。
    - 如果穩定獲利：可以考慮保持原樣，或者稍微放大風險比例來擴大獲利。
    - 參數合理範圍：停損 0.02~0.08，停利 0.05~0.20，風險 0.01~0.05。
    
    請以嚴格的 JSON 格式回覆。絕對不要包含任何 Markdown 標籤 (例如 ```json )，直接輸出 JSON 字串。
    必須包含以下格式：
    {{
        "STOP_LOSS_PCT": (填入你的建議浮點數),
        "TAKE_PROFIT_PCT": (填入你的建議浮點數),
        "RISK_PER_TRADE": (填入你的建議浮點數),
        "REASON": "(繁體中文，100字內解釋你為什麼這樣調整)"
    }}
    """

    try:
        print("🤔 AI 教練正在閱讀帳本並思考新戰略，請稍候...")
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        # 暴力清理 LLM 常常不小心加上去的 Markdown 程式碼區塊符號
        result_text = re.sub(r'^```json', '', result_text, flags=re.IGNORECASE)
        result_text = re.sub(r'^```', '', result_text)
        result_text = re.sub(r'```$', '', result_text).strip()

        # 解析 JSON
        new_params = json.loads(result_text)
        
        # 將新參數存入 dynamic_config.json
        with open("dynamic_config.json", "w", encoding="utf-8") as f:
            json.dump(new_params, f, indent=4, ensure_ascii=False)
            
        print(f"\n✅ 進化成功！新參數已寫入 dynamic_config.json")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"📊 新停損: {new_params['STOP_LOSS_PCT']*100}%")
        print(f"🎯 新停利: {new_params['TAKE_PROFIT_PCT']*100}%")
        print(f"💰 新風險: {new_params['RISK_PER_TRADE']*100}%")
        print(f"💡 AI 教練評語: {new_params['REASON']}")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("下一次啟動 main.py 時，系統將自動套用這組新戰略！")
        
    except json.JSONDecodeError:
        print(f"⚠️ 進化失敗：AI 回傳的格式不是標準 JSON。原始回覆內容：\n{result_text}")
    except Exception as e:
        print(f"⚠️ 進化過程發生預期外錯誤: {e}")

if __name__ == "__main__":
    run_evolution()
