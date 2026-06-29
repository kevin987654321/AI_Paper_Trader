import pandas as pd
from google import genai
import json
import os
import re
from datetime import datetime
import config

def analyze_ledger(universe_name, ledger_path):
    """讀取指定的帳本與淨值歷史，計算包含持股的真實績效指標"""
    if not os.path.exists(ledger_path):
        return None

    try:
        df = pd.read_csv(ledger_path)
        sell_records = df[df['Action'] == 'SELL']
        total_trades = len(sell_records)
        
        initial_cash = getattr(config, 'INITIAL_CAPITAL', 100000)
        current_equity = initial_cash
        current_cash = df.iloc[-1]['Cash_Left']
        
        # 🌟 核心修正：從 nav_history.csv 抓取包含「持股現值」的真實總資產
        nav_path = "data/nav_history.csv"
        if os.path.exists(nav_path):
            nav_df = pd.read_csv(nav_path)
            if universe_name in nav_df.columns and not nav_df.empty:
                current_equity = float(nav_df.iloc[-1][universe_name])
        else:
            current_equity = current_cash
            
        # 計算真實的投資報酬率 (ROI)
        roi = ((current_equity - initial_cash) / initial_cash) * 100
        
        report = f"""
        - 初始資金: {initial_cash:,.0f} 元
        - 目前帳戶現金: {current_cash:,.0f} 元
        - 真實總資產 (含持股現值): {current_equity:,.0f} 元
        - 真實總報酬率 (ROI): {roi:.2f}%
        """
        
        if total_trades > 0:
            report += f"        - 總共完成結清交易: {total_trades} 筆\n"
        else:
            report += "        - 當前戰況提示: 目前暫無平倉紀錄，資金正處於現金部位或持股未實現狀態。\n"
            
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
    請根據「真實總報酬率」判斷是否需要微調參數。
    - 參數合理範圍：ATR倍數介於 {atr_range}，風險介於 {risk_range}。
    - 若嚴重虧損(<-5%)：縮小風險或降低 ATR 容忍度。
    - 若穩定獲利或持平：微調放大參數以擴大獲利，或「保持現狀」。
    - 💡 關鍵指示：如果獲利或虧損幅度不到 1%，代表多數資金可能剛進場或空手，強烈建議給出「保持原樣」的決策！
    
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
        
        result_text = response.text.strip()
        result_text = re.sub(r'^```json', '', result_text, flags=re.IGNORECASE)
        result_text = re.sub(r'^```', '', result_text)
        result_text = re.sub(r'```$', '', result_text).strip()

        return json.loads(result_text)
        
    except Exception as e:
        print(f"⚠️ {universe_name} 進化過程發生預期外錯誤: {e}")
        return {
            f"{universe_name}_ATR": current_atr, 
            f"{universe_name}_RISK": current_risk,
            f"REASON_{universe_name}": "進化失敗，觸發防護機制維持原設定"
        }

def run_evolution():
    """執行雙重動態宇宙的進化流程"""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🧬 啟動雙重動態宇宙自我進化機制...")
    
    final_dynamic_config = {}

    # 🌟 讀取最原始的健康參數，避免被上一次嚇壞的錯誤參數洗腦
    base_dyn1_atr = getattr(config, 'DYN_1_ATR', 3.0)
    base_dyn1_risk = getattr(config, 'DYN_1_RISK', 0.03)
    base_dyn2_atr = getattr(config, 'DYN_2_ATR', 2.0)
    base_dyn2_risk = getattr(config, 'DYN_2_RISK', 0.02)

    # ==========================================
    # 🚀 1. 處理 DYN_1 (動態積極組)
    # ==========================================
    print("\n[讀取] DYN_1 動態積極組真實績效...")
    perf_dyn_1 = analyze_ledger("DYN_1", getattr(config, 'LEDGER_DYN_1', "data/ledger_dyn_1_agg.csv"))
    
    params_dyn_1 = evolve_universe(
        universe_name="DYN_1",
        performance_data=perf_dyn_1,
        current_atr=base_dyn1_atr,
        current_risk=base_dyn1_risk,
        atr_range="2.5 ~ 4.0", 
        risk_range="0.02 ~ 0.05"
    )
    final_dynamic_config.update(params_dyn_1)

    # ==========================================
    # 🛡️ 2. 處理 DYN_2 (動態穩健組)
    # ==========================================
    print("\n[讀取] DYN_2 動態穩健組真實績效...")
    perf_dyn_2 = analyze_ledger("DYN_2", getattr(config, 'LEDGER_DYN_2', "data/ledger_dyn_2_con.csv"))
    
    params_dyn_2 = evolve_universe(
        universe_name="DYN_2",
        performance_data=perf_dyn_2,
        current_atr=base_dyn2_atr,
        current_risk=base_dyn2_risk,
        atr_range="1.5 ~ 2.5", 
        risk_range="0.01 ~ 0.02"
    )
    final_dynamic_config.update(params_dyn_2)

    # ==========================================
    # 💾 3. 合併結果並寫入檔案
    # ==========================================
    with open("dynamic_config.json", "w", encoding="utf-8") as f:
        json.dump(final_dynamic_config, f, indent=4, ensure_ascii=False)
        
    log_path = "data/evolution_history_log.txt"
    os.makedirs("data", exist_ok=True)
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write("==================================================\n")
        f.write(f"🕒 矩陣進化時間: {now_str}\n")
        f.write("--------------------------------------------------\n")
        f.write("🚀 [DYN_1 動態積極組]\n")
        f.write(f"  - 新 ATR: {final_dynamic_config.get('DYN_1_ATR')} | 新風險: {final_dynamic_config.get('DYN_1_RISK')}\n")
        f.write(f"  - 💡 AI 評語: {final_dynamic_config.get('REASON_DYN_1')}\n")
        f.write("--------------------------------------------------\n")
        f.write("🛡️ [DYN_2 動態穩健組]\n")
        f.write(f"  - 新 ATR: {final_dynamic_config.get('DYN_2_ATR')} | 新風險: {final_dynamic_config.get('DYN_2_RISK')}\n")
        f.write(f"  - 💡 AI 評語: {final_dynamic_config.get('REASON_DYN_2')}\n")
        f.write("==================================================\n\n")
        
    print(f"\n✅ 進化完成！全新基因已注入 dynamic_config.json")
    print(f"📜 歷史戰略反思軌跡已同步追加至 {log_path}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🚀 [DYN_1 動態積極組]")
    print(f"    📈 新 ATR: {final_dynamic_config.get('DYN_1_ATR')} | 💰 新風險: {final_dynamic_config.get('DYN_1_RISK')}")
    print(f"    💡 評語: {final_dynamic_config.get('REASON_DYN_1')}")
    print("────────────────────────────────")
    print("🛡️ [DYN_2 動態穩健組]")
    print(f"    📉 新 ATR: {final_dynamic_config.get('DYN_2_ATR')} | 💰 新風險: {final_dynamic_config.get('DYN_2_RISK')}")
    print(f"    💡 評語: {final_dynamic_config.get('REASON_DYN_2')}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

if __name__ == "__main__":
    run_evolution()
