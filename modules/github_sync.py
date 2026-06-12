import os
import subprocess
from datetime import datetime

def push_to_github(commit_message="🤖 AI Bot: 更新帳本與參數"):
    """
    將本地端的變更自動推送到 GitHub。
    注意：雲端環境需要設定 GITHUB_TOKEN 環境變數。
    """
    try:
        # 1. 加入所有變更 (包含 data/paper_ledger.csv 與 dynamic_config.json)
        subprocess.run(["git", "add", "data/paper_ledger.csv", "dynamic_config.json"], check=True)
        
        # 2. 提交變更 (加入 [skip ci] 是為了防止觸發雲端平台無限重新部署)
        full_message = f"{commit_message} [skip ci]"
        subprocess.run(["git", "commit", "-m", full_message], check=True)
        
        # 3. 取得環境變數中的 GitHub Token 並設定遠端 URL
        # 格式: https://<TOKEN>@github.com/<你的帳號>/<你的儲存庫>.git
        github_token = os.environ.get("GITHUB_TOKEN")
        github_repo = os.environ.get("GITHUB_REPO") # 例如: kevin987654321/AI_Paper_Trader
        
        if github_token and github_repo:
            remote_url = f"https://{github_token}@github.com/{github_repo}.git"
            subprocess.run(["git", "push", remote_url, "main"], check=True)
            print("☁️ [同步成功] 帳本與設定已安全備份至 GitHub！")
        else:
            print("⚠️ 找不到 GITHUB_TOKEN 或 GITHUB_REPO 環境變數，僅保存在本地端。")
            
    except subprocess.CalledProcessError as e:
        # 如果沒有東西可以 commit，Git 會報錯，這是正常的，忽略即可
        if "nothing to commit" not in str(e):
            print(f"⚠️ GitHub 同步發生錯誤: {e}")
