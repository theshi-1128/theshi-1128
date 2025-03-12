import requests
import os
import re

# 你的 GitHub 用户名
USERNAME = "theshi-1128"

# GitHub Token（需要有 "public_repo" 权限），可以存储在 GitHub Secrets 中
TOKEN = os.getenv("THESHI")

# 获取用户的所有仓库的 Star 数量
def get_user_stars():
    url = f"https://api.github.com/users/{USERNAME}/repos"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    repos = requests.get(url, headers=headers).json()
    total_stars = sum(repo["stargazers_count"] for repo in repos if "stargazers_count" in repo)
    
    return total_stars

# 获取用户作为 Contributor 贡献的仓库 Star 数量
def get_contributed_stars():
    url = f"https://api.github.com/users/{USERNAME}/repos"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    repos = requests.get(url, headers=headers).json()
    contributed_stars = sum(repo["stargazers_count"] for repo in repos if "stargazers_count" in repo)
    
    return contributed_stars

# 更新 README.md
def update_readme():
    user_stars = get_user_stars()
    contributed_stars = get_contributed_stars()
    total_stars = user_stars + contributed_stars

    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    content = re.sub(r"<!--START_TOTAL_STARS-->.*?<!--END_TOTAL_STARS-->", 
                     f"<!--START_TOTAL_STARS-->{total_stars}<!--END_TOTAL_STARS-->", content)

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)

update_readme()
