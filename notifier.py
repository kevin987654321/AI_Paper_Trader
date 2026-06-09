import requests
import os

def send_line_message(msg_text):
    """將格式化好的訊息推播到 LINE"""
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = os.environ.get("LINE_USER_ID")
    
    if not token or not user_id:
        print("⚠️ 未設定 LINE 金鑰，無法發送 LINE 通知。")
        print(msg_text) # 沒設定就印在終端機加減看
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "to": user_id,
        "messages": [{"type": "text", "text": msg_text}]
    }
    
    try:
        response = requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=data)
        response.raise_for_status() # 檢查是否有 HTTP 錯誤
    except Exception as e:
        print(f"❌ LINE 傳送失敗: {e}")