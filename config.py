import os

# ==========================================
# ⚙️ 基礎系統設定
# ==========================================
INITIAL_CAPITAL = 100000  # 初始模擬資金 10 萬
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# ==========================================
# 🌌 5.0 終極版：核心衛星配置名單
# ==========================================
TECH_TICKERS = ["2330.TW", "2317.TW", "2454.TW", "2308.TW", "2382.TW"] # 科技核心 (最多持股 3 檔)
DEFENSIVE_TICKERS = ["2881.TW", "2886.TW", "2891.TW", "2603.TW", "2002.TW"] # 傳產金融衛星 (最多持股 2 檔)

# 自動合併為全天候觀察清單
WATCHLIST = TECH_TICKERS + DEFENSIVE_TICKERS

# ==========================================
# 🗂️ 四重平行宇宙帳本路徑
# ==========================================
LEDGER_DYN_1 = "data/ledger_dyn_1_agg.csv"  # 🚀 AI 動態積極組 (每週調整)
LEDGER_DYN_2 = "data/ledger_dyn_2_con.csv"  # 🛡️ AI 動態穩健組 (每週調整)
LEDGER_STA_1 = "data/ledger_sta_1_agg.csv"  # ⚔️ 靜態對照積極組 (死守參數)
LEDGER_STA_2 = "data/ledger_sta_2_con.csv"  # 🧱 靜態對照穩健組 (死守參數)

# ==========================================
# 🧬 四重平行宇宙預設基因 (單筆風險 / ATR停損倍數)
# ==========================================
# 【積極型】 (Aggressive)：單筆風險 3%，ATR 3.0倍 (抱得緊，容忍大震盪以換取大波段)
STA_1_RISK = 0.03
STA_1_ATR = 3.0
DYN_1_RISK = 0.03
DYN_1_ATR = 3.0

# 【穩健型】 (Conservative)：單筆風險 2%，ATR 2.0倍 (防禦極高，破線快跑)
STA_2_RISK = 0.02
STA_2_ATR = 2.0
DYN_2_RISK = 0.02
DYN_2_ATR = 2.0

# (註：DYN_1 與 DYN_2 雖然這裡有預設值，但未來每週末會被 evolution.py 產生的 dynamic_config.json 覆蓋)
