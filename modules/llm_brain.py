def generate_daily_report():
    """讀取今日日誌與帳本，讓 Gemini 產生收盤總結報告"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "⚠️ 找不到 Gemini API Key，無法產生報告"

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
        # 💡 統一換成新版 Client 寫法，並指定使用 gemini-2.5-flash
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"⚠️ 收盤報告生成失敗：{e}"
