#!/usr/bin/env python3
# update_stars.py
# 功能（增强版）：
#  1) 使用 GITHUB_TOKEN 获取当前用户所有 repo（type=owner），计算 total = sum(stars)+sum(forks)
#  2) 尝试多种方式把 total 写回 README.md：
#     - 优先替换 <!--START_TOTAL_SCORE-->...<!--END_TOTAL_SCORE--> 占位符
#     - 若无占位符，尝试替换常见的 "Total Stars & Forks:" / "Total Stars + Forks:" / "Total Stars:" 行中数字
#     - 若仍无匹配，尝试在 "### ⭐ Github Status:" 标题下面插入一行带占位符的统计行
#     - 最后兜底：若以上都找不到，则追加到 README 末尾
#
#  这样可以避免占位符不存在导致脚本直接失败的情况，同时兼容你现有 README 的不同写法。

import os
import re
import sys
import requests
from typing import List, Dict, Tuple

TOKEN = os.getenv("GITHUB_TOKEN")
if not TOKEN:
    print("Error: GITHUB_TOKEN environment variable not set.", file=sys.stderr)
    sys.exit(1)

HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "update-stars-script"
}


def get_authenticated_user() -> str:
    resp = requests.get("https://api.github.com/user", headers=HEADERS, timeout=30)
    resp.raise_for_status()
    login = resp.json().get("login")
    if not login:
        raise RuntimeError("Could not determine authenticated user's login.")
    return login


def fetch_all_repos(user: str) -> List[Dict]:
    repos = []
    page = 1
    per_page = 100
    while True:
        url = f"https://api.github.com/users/{user}/repos"
        params = {"per_page": per_page, "page": page, "type": "owner", "sort": "full_name"}
        resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            raise RuntimeError(f"Unexpected response fetching repos: {data}")
        repos.extend(data)
        if len(data) < per_page:
            break
        page += 1
    return repos


def calculate_total_score(repos: List[Dict]) -> Tuple[int, int, int]:
    total_stars = sum(int(r.get("stargazers_count", 0) or 0) for r in repos)
    total_forks = sum(int(r.get("forks_count", 0) or 0) for r in repos)
    total = total_stars + total_forks
    return total, total_stars, total_forks


def replace_placeholder(text: str, total: int) -> Tuple[str, bool]:
    """
    优先使用 <!--START_TOTAL_SCORE-->...<!--END_TOTAL_SCORE--> 占位符替换
    """
    pattern = re.compile(r"(<!--START_TOTAL_SCORE-->)(.*?)(<!--END_TOTAL_SCORE-->)", re.S)
    if pattern.search(text):
        new_text = pattern.sub(lambda m: m.group(1) + str(total) + m.group(3), text, count=1)
        return new_text, True
    return text, False


def replace_common_line(text: str, total: int) -> Tuple[str, bool]:
    """
    如果没有占位符，尝试匹配 README 中常见的“Total Stars & Forks”或“Total Stars + Forks”或“Total Stars”这类行并替换数字。
    例子匹配：
      > 🌟 **Total Stars + Forks:** 123
      > ✨ Total Stars & Forks: 123
      * Total Stars & Forks: 123
    """
    # 匹配包含 "Total" 和 "Stars" 的行，允许同时出现 "Forks" 或不出现
    pattern = re.compile(r"^([ \t>*-]*.*Total\s+Stars(?:\s*(?:\+|&|and)?\s*Forks)?\s*[:：]\s*)(\S+)(.*)$",
                         re.IGNORECASE | re.MULTILINE)
    def _repl(m):
        return m.group(1) + str(total) + m.group(3)
    new_text, n = pattern.subn(_repl, text, count=1)
    return new_text, n > 0


def insert_under_status_heading(text: str, total: int) -> Tuple[str, bool]:
    """
    如果没匹配到任何行，尝试在 "### ⭐ Github Status:" 这一行下面插入统计占位行。
    """
    heading_pattern = re.compile(r"^(###\s*⭐\s*Github Status:.*)$", re.MULTILINE)
    m = heading_pattern.search(text)
    insert_line = f"\n> 🌟 **Total Stars + Forks:** <!--START_TOTAL_SCORE-->{total}<!--END_TOTAL_SCORE-->\n"
    if m:
        # 在匹配行之后插入
        idx = m.end(1)
        new_text = text[:idx] + insert_line + text[idx:]
        return new_text, True
    return text, False


def append_to_end(text: str, total: int) -> Tuple[str, bool]:
    """
    兜底：追加到 README 末尾
    """
    append_line = f"\n---\n> 🌟 **Total Stars + Forks:** <!--START_TOTAL_SCORE-->{total}<!--END_TOTAL_SCORE-->\n"
    new_text = text + append_line
    return new_text, True


def update_readme_robust(total: int) -> None:
    readme_path = "README.md"
    if not os.path.exists(readme_path):
        raise FileNotFoundError("README.md not found in repo root.")

    with open(readme_path, "r", encoding="utf-8") as f:
        text = f.read()

    # 1) 占位符替换
    new_text, done = replace_placeholder(text, total)
    if done:
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(new_text)
        print("Replaced using explicit placeholder <!--START_TOTAL_SCORE-->...<!--END_TOTAL_SCORE-->.")
        return

    # 2) 替换常见的 Total 行
    new_text, done = replace_common_line(text, total)
    if done:
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(new_text)
        print("Replaced an existing 'Total Stars' line in README.")
        return

    # 3) 在 Github Status 标题下插入（如果存在该标题）
    new_text, done = insert_under_status_heading(text, total)
    if done:
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(new_text)
        print("Inserted total line under '### ⭐ Github Status:' heading.")
        return

    # 4) 兜底追加到末尾
    new_text, done = append_to_end(text, total)
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(new_text)
    print("Appended total line at README end as a fallback.")


def main():
    try:
        user = get_authenticated_user()
        print(f"Authenticated as: {user}")

        repos = fetch_all_repos(user)
        print(f"Fetched {len(repos)} repositories (type=owner).")

        total, stars, forks = calculate_total_score(repos)
        print(f"stars: {stars}, forks: {forks}, total: {total}")

        update_readme_robust(total)
        print("README update completed successfully.")

    except requests.HTTPError as e:
        print("HTTP Error:", e, file=sys.stderr)
        if e.response is not None:
            try:
                print(e.response.json(), file=sys.stderr)
            except Exception:
                print(e.response.text, file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print("Error:", e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
