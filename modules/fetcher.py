import yfinance as yf
import pandas as pd

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

def get_latest_news(ticker="2330.TW"):
    """
    獲取該股票的最新財經新聞標題與摘要
    使用 yfinance 內建的新聞功能，直接抓取 Yahoo Finance 的英文新聞，
    Gemini 讀得懂英文，且會用中文回覆你，所以不用擔心。
    """
    try:
        stock = yf.Ticker(ticker)
        news_items = stock.news
        
        if not news_items:
            return "目前沒有找到關於該公司的最新新聞。"
            
        # 把前 3 則新聞的標題和連結組合起來，餵給 Gemini
        news_text = "以下是最新市場新聞：\n\n"
        for item in news_items[:3]: # 只取最新的 3 篇
            news_text += f"標題: {item.get('title', '無標題')}\n"
            news_text += f"連結: {item.get('link', '無連結')}\n\n"
            
        return news_text
        
    except Exception as e:
        print(f"⚠️ 抓取新聞時發生錯誤: {e}")
        return "無法取得新聞。"