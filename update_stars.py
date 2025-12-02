#!/usr/bin/env python3
# update_stars.py
# 功能：使用 GITHUB_TOKEN 获取当前用户所有 repo（owner 类型），计算 total = sum(stars)+sum(forks)
# 并将结果替换 README.md 中的 <!--START_TOTAL_SCORE-->...<!--END_TOTAL_SCORE-->
# 修复：避免正则反向引用与数字连写导致的问题（使用 lambda 回调进行替换）

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
    """
    Fetch all repositories for the given user (type=owner). Handles pagination.
    """
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
            # If GitHub returns a dict (rate limit, error), raise for easier debugging
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


def update_readme_total(total: int) -> None:
    readme_path = "README.md"
    if not os.path.exists(readme_path):
        raise FileNotFoundError("README.md not found in repo root.")

    with open(readme_path, "r", encoding="utf-8") as f:
        text = f.read()

    pattern = re.compile(r"(<!--START_TOTAL_SCORE-->)(.*?)(<!--END_TOTAL_SCORE-->)", re.S)

    if not pattern.search(text):
        raise RuntimeError("Placeholder <!--START_TOTAL_SCORE-->...<!--END_TOTAL_SCORE--> not found in README.md")

    # Use lambda to avoid backreference ambiguity (e.g. \1 followed by digits)
    new_text = pattern.sub(lambda m: m.group(1) + str(total) + m.group(3), text, count=1)

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(new_text)

    print(f"Updated README.md: total (stars+forks) = {total}")


def main():
    try:
        user = get_authenticated_user()
        print(f"Authenticated as: {user}")

        repos = fetch_all_repos(user)
        print(f"Fetched {len(repos)} repositories (type=owner).")

        total, stars, forks = calculate_total_score(repos)
        print(f"stars: {stars}, forks: {forks}, total: {total}")

        update_readme_total(total)

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
