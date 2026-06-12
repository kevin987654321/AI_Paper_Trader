# 🏆 新增：多重標的雷達觀察名單 (可自由增減台股標的)
WATCHLIST = ["2330.TW", "2317.TW", "2454.TW", "2308.TW", "2382.TW"] 

MAX_POSITIONS = 3         # 🛡️ 防線 1：整個帳戶最多同時持有 3 檔股票部位
POSITION_SIZE_PCT = 0.3   # 🛡️ 防線 2：單一檔股票最多只能吃掉「當下可用現金的 30%」，避免一檔就把錢扣光

TICKER = "2330.TW"        # 保留原本的，做為防呆預設
INITIAL_CAPITAL = 100000  # 初始模擬資金 10 萬
RISK_PER_TRADE = 0.02     # 單筆承受風險 2%
STOP_LOSS_PCT = 0.02      # 停損 2% 
TAKE_PROFIT_PCT = 0.10    # 停利 10%
VIX_THRESHOLD = 35

# Gemini API 金鑰
GEMINI_API_KEY = "AQ.Ab8RN6JilA-HBeMhS4WYBokJM8UWfMiHIy9zg8chNNcJc4nOcQ"

# 檔案路徑
LEDGER_PATH = "data/paper_ledger.csv"

import json
import os

# 會被 AI 改變的動態參數 (以下為預設安全值，若找不到 AI 設定檔則套用此處)
RISK_PER_TRADE = 0.02     # 單筆承受風險 2%
STOP_LOSS_PCT = 0.02      # 停損 2% 
TAKE_PROFIT_PCT = 0.10    # 停利 10%

DYNAMIC_CONFIG_PATH = "dynamic_config.json"

if os.path.exists(DYNAMIC_CONFIG_PATH):
    try:
        with open(DYNAMIC_CONFIG_PATH, "r", encoding="utf-8") as f:
            dynamic_params = json.load(f)
            
        # 如果 AI 有產出新參數，就覆寫上面的預設值
        if "RISK_PER_TRADE" in dynamic_params:
            RISK_PER_TRADE = dynamic_params["RISK_PER_TRADE"]
        if "STOP_LOSS_PCT" in dynamic_params:
            STOP_LOSS_PCT = dynamic_params["STOP_LOSS_PCT"]
        if "TAKE_PROFIT_PCT" in dynamic_params:
            TAKE_PROFIT_PCT = dynamic_params["TAKE_PROFIT_PCT"]
            
        print("🔧 [系統設定] 已成功載入 AI 最新進化參數！")
    except Exception as e:
        print(f"⚠️ 讀取 AI 動態設定失敗，將強制使用預設安全參數: {e}")
