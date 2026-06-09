from modules import llm_brain, notifier

def run_daily_summary():
    """每日收盤後執行一次，產出總結報告並發送 LINE"""
    print("啟動收盤總結程序...")
    
    # 呼叫 Gemini 大腦生成報告
    report_msg = llm_brain.generate_daily_report()
    
    # 發送 LINE 訊息
    notifier.send_line_message(report_msg)
    print("✅ 收盤報告已傳送至 LINE！")

if __name__ == "__main__":
    run_daily_summary()