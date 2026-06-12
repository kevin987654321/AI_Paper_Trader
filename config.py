# 目標股票與參數
TICKER = "2330.TW"        # 台積電
INITIAL_CAPITAL = 100000  # 初始模擬資金 10 萬
RISK_PER_TRADE = 0.02     # 單筆承受風險 2% (最多虧損總資金的 2%)
STOP_LOSS_PCT = 0.02      # 停損 2% (股價跌 2% 就跑)
TAKE_PROFIT_PCT = 0.10    # 停利 10% (股價漲 10% 就收割)
VIX_THRESHOLD = 35        # 防呆機制：VIX 恐慌指數上限

# Gemini API 金鑰
GEMINI_API_KEY = "AQ.Ab8RN6JilA-HBeMhS4WYBokJM8UWfMiHIy9zg8chNNcJc4nOcQ"

# 檔案路徑
LEDGER_PATH = "data/paper_ledger.csv"
