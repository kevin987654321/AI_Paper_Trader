import pandas as pd
from google import genai
import json
import os
import re
from datetime import datetime
import config

def analyze_ledger(ledger_path):
    """讀取指定的帳本路徑，計算基礎績效指標"""
    if not os.path.exists(ledger_path):
        return None

    try:
        df = pd.read_csv(ledger_path)
        sell_records = df[df['Action'] == 'SELL']

        if len(sell_records) == 0:
            return "目前還沒有賣出紀錄（皆為持倉或空手），無法計算實際損益勝率。"

        # 計算目前的投資報酬率 (ROI)
        initial_cash = config.INITIAL_CAPITAL
        current_cash = df.iloc[-1]['Cash_Left']
        roi = ((current_cash - initial_cash) / initial_cash) * 100
        total_trades = len(sell_records)
        
        report = f"""
        - 初始資金: {initial_cash:,.0f} 元
        - 目前現金: {current_cash:,.0f} 元
        - 總報酬率 (ROI): {roi:.2f}%
        - 總共完成交易: {total_trades} 筆
        """
        return report
        
    except Exception as e:
        print(f"分析帳本 {ledger_path} 失敗: {e}")
        return None

def evolve_universe(universe_name, performance_data, current_atr, current_risk, atr_range, risk_range):
    """呼叫 Gemini 進行單一宇宙的反思，並回傳新參數的字典"""
    if not performance_data or "無法計算" in performance_data:
        print(f"⚠️ {universe_name} 交易樣本不足，本週維持原設定。")
        return {
            f"{universe_name}_ATR": current_atr, 
            f"{universe_name}_RISK": current_risk,
            f"REASON_{universe_name}": "樣本不足，維持原樣"
        }

    prompt = f"""
    你現在是一位頂尖的量化交易策略大師。
    正在負責優化「{universe_name}」宇宙的交易策略。
    目前的參數設定如下：
    - ATR停損倍數 ({universe_name}_ATR): {current_atr}
    - 單筆資金風險比例 ({universe_name}_RISK): {current_risk}

    近期的真實交易績效結算如下：
    {performance_data}

    任務：
    請根據「總報酬率」判斷是否需要微調參數。
    - 參數合理範圍：ATR倍數介於 {atr_range}，風險介於 {risk_range}。
    - 若嚴重虧損：縮小風險或降低 ATR 容忍度。
    - 若穩定獲利：可微調放大參數以擴大獲利，或保持現狀。
    
    請以嚴格的 JSON 格式回覆。絕對不要包含任何 Markdown 標籤 (例如 ```json )，直接輸出 JSON 字串。
    必須包含以下格式：
    {{
        "{universe_name}_ATR": (填入建議浮點數),
        "{universe_name}_RISK": (填入建議浮點數),
        "REASON_{universe_name}": "(繁體中文，50字內解釋調整原因)"
    }}
    """

    try:
        print(f"🤔 AI 正在思考 {universe_name} 的新戰略...")
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=prompt
        )
        
        # 暴力清理 Markdown 標籤
        result_text = response.text.strip()
        result_text = re.sub(r'^```json', '', result_text, flags=re.IGNORECASE)
        result_text = re.sub(r'^```', '', result_text)
        result_text = re.sub(r'```$', '', result_text).strip()

        return json.loads(result_text)
        
    except Exception as e:
        print(f"⚠️ {universe_name} 進化過程發生預期外錯誤: {e}")
        # 若發生錯誤，回傳原始設定以保證系統能繼續運行
        return {
            f"{universe_name}_ATR": current_atr, 
            f"{universe_name}_RISK": current_risk,
            f"REASON_{universe_name}": "進化失敗，觸發防護機制維持原設定"
        }

def run_evolution():
    """執行雙重動態宇宙的進化流程"""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🧬 啟動雙重動態宇宙自我進化機制...")
    
    final_dynamic_config = {}

    # ==========================================
    # 🚀 1. 處理 DYN_1 (動態積極組)
    # ==========================================
    print("\n[讀取] DYN_1 動態積極組帳本...")
    perf_dyn_1 = analyze_ledger(config.LEDGER_DYN_1)
    
    # 積極組允許較大的 ATR 容忍度與風險
    params_dyn_1 = evolve_universe(
        universe_name="DYN_1",
        performance_data=perf_dyn_1,
        current_atr=config.DYN_1_ATR,
        current_risk=config.DYN_1_RISK,
        atr_range="2.5 ~ 4.0", 
        risk_range="0.02 ~ 0.05"
    )
    final_dynamic_config.update(params_dyn_1)

    # ==========================================
    # 🛡️ 2. 處理 DYN_2 (動態穩健組)
    # ==========================================
    print("\n[讀取] DYN_2 動態穩健組帳本...")
    perf_dyn_2 = analyze_ledger(config.LEDGER_DYN_2)
    
    # 穩健組嚴格限制防禦力，破線快跑
    params_dyn_2 = evolve_universe(
        universe_name="DYN_2",
        performance_data=perf_dyn_2,
        current_atr=config.DYN_2_ATR,
        current_risk=config.DYN_2_RISK,
        atr_range="1.5 ~ 2.5", 
        risk_range="0.01 ~ 0.02"
    )
    final_dynamic_config.update(params_dyn_2)

    # ==========================================
    # 💾 3. 合併結果並寫入檔案
    # ==========================================
    with open("dynamic_config.json", "w", encoding="utf-8") as f:
        json.dump(final_dynamic_config, f, indent=4, ensure_ascii=False)
        
    print(f"\n✅ 進化完成！全新基因已注入 dynamic_config.json")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🚀 [DYN_1 動態積極組]")
    print(f"   📈 新 ATR: {final_dynamic_config.get('DYN_1_ATR')} | 💰 新風險: {final_dynamic_config.get('DYN_1_RISK')}")
    print(f"   💡 評語: {final_dynamic_config.get('REASON_DYN_1')}")
    print("────────────────────────────────")
    print("🛡️ [DYN_2 動態穩健組]")
    print(f"   📉 新 ATR: {final_dynamic_config.get('DYN_2_ATR')} | 💰 新風險: {final_dynamic_config.get('DYN_2_RISK')}")
    print(f"   💡 評語: {final_dynamic_config.get('REASON_DYN_2')}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

if __name__ == "__main__":
    run_evolution()
