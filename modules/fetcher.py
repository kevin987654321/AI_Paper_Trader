import yfinance as yf
import pandas as pd
import requests
import xml.etree.ElementTree as ET

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

def get_latest_news(ticker):
    """
    使用 Google News RSS 抓取台股即時新聞，穩定度極高。
    """
    # 把 "2330.TW" 變成 "2330"，加上 "台股" 關鍵字讓搜尋更精準
    stock_id = ticker.replace(".TW", "").replace(".TWO", "")
    query = f"{stock_id} 台股"
    
    # Google News RSS 專用網址 (限定台灣繁體中文)
    url = f"https://news.google.com/rss/search?q={query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    
    try:
        # 偽裝成瀏覽器，避免被阻擋
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 解析 XML 格式
        root = ET.fromstring(response.text)
        news_list = []
        
        # 抓取最新前 5 則新聞
        for item in root.findall('.//item')[:5]:
            title = item.find('title').text if item.find('title') is not None else "無標題"
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else "未知時間"
            
            # 清理過長的標題後綴 (通常會附帶新聞媒體名稱)
            clean_title = title.split(" - ")[0] 
            
            news_list.append(f"標題: {clean_title}\n發布時間: {pub_date}")
            
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
