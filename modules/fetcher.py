import yfinance as yf
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup  # 🏆 新增：用來解析網頁抓取內文

def get_stock_data(ticker="2330.TW", period="60d"):
    """獲取股票歷史數據"""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        
        if df.empty:
            print(f"⚠️ 無法獲取 {ticker} 的數據，請檢查代碼或網路。")
            return None
            
        return df
    except Exception as e:
        print(f"⚠️ 抓取數據時發生錯誤: {e}")
        return None

def fetch_article_content(url):
    """
    🏆 新增模組：進入新聞網址，抓取網頁中的段落文字
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # 設定較短的 timeout，避免卡在某個沒反應的網站
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        
        # 使用 BeautifulSoup 解析 HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 抓取所有 <p> (段落) 標籤內的文字
        paragraphs = soup.find_all('p')
        content = " ".join([p.get_text(strip=True) for p in paragraphs])
        
        # 過濾掉太短的無效內容 (例如只有版權宣告)
        if len(content) < 50:
            return "無法擷取有效內文或內容受阻擋。"
            
        # 💡 Token 防護機制：只取前 500 字，足夠讓 Gemini 判斷情緒，又不會浪費 API 額度
        if len(content) > 500:
            content = content[:500] + "...(後略)"
            
        return content
        
    except Exception as e:
        # 如果該新聞網站擋爬蟲，就回傳錯誤訊息，不影響整體系統運作
        return "網站阻擋爬蟲或連線逾時，無法擷取內文。"

def get_latest_news(ticker):
    """
    使用 Google News RSS 抓取台股即時新聞與內文摘要
    """
    stock_id = ticker.replace(".TW", "").replace(".TWO", "")
    query = f"{stock_id} 台股"
    
    url = f"https://news.google.com/rss/search?q={query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        root = ET.fromstring(response.text)
        news_list = []
        
        # 抓取最新前 5 則新聞
        print(f"📰 正在為 {ticker} 爬取最新新聞與內文，請稍候...")
        for item in root.findall('.//item')[:5]:
            title = item.find('title').text if item.find('title') is not None else "無標題"
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else "未知時間"
            
            # 🏆 取得新聞的真實網址
            link = item.find('link').text if item.find('link') is not None else ""
            
            clean_title = title.split(" - ")[0] 
            
            # 呼叫我們剛剛寫好的模組，去該網址抓內文
            article_content = fetch_article_content(link) if link else "無連結可擷取。"
            
            news_item = f"標題: {clean_title}\n發布時間: {pub_date}\n內文重點: {article_content}"
            news_list.append(news_item)
            
        if not news_list:
            return "近期無相關新聞。"
            
        return "以下是最新市場新聞：\n\n" + "\n---\n".join(news_list)
        
    except requests.exceptions.RequestException as e:
        print(f"⚠️ 網路連線錯誤 (抓取新聞): {e}")
        return "無法連線至新聞伺服器。"
    except ET.ParseError as e:
        print(f"⚠️ XML 解析錯誤 (抓取新聞): {e}")
        return "新聞格式解析失敗。"
    except Exception as e:
        print(f"⚠️ 發生未知錯誤 (抓取新聞): {e}")
        return "抓取新聞發生未知錯誤。"
