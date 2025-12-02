#!/usr/bin/env python3
# update_stars.py
# 功能：使用 GITHUB_TOKEN 获取当前用户所有 repo，计算 total = sum(stars)+sum(forks)
# 并将结果替换 README.md 中的 <!--START_TOTAL_SCORE-->...<!--END_TOTAL_SCORE-->

import os
import re
import sys
import requests

TOKEN = os.getenv("GITHUB_TOKEN")
if not TOKEN:
    print("Error: GITHUB_TOKEN environment variable not set.", file=sys.stderr)
    sys.exit(1)

HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "update-stars-script"
}

def get_authenticated_user():
    r = requests.get("https://api.github.com/user", headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json().get("login")

def fetch_all_repos(user):
    repos = []
    page = 1
    per_page = 100
    while True:
        url = f"https://api.github.com/users/{user}/repos"
        params = {"per_page": per_page, "page": page, "type": "owner", "sort": "full_name"}
        r = requests.get(url, headers=HEADERS, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        repos.extend(data)
        if len(data) < per_page:
            break
        page += 1
    return repos

def calculate_total_score(repos):
    total_stars = sum(r.get("stargazers_count", 0) for r in repos)
    total_forks = sum(r.get("forks_count", 0) for r in repos)
    total = total_stars + total_forks
    return total, total_stars, total_forks

def update_readme(total):
    readme_path = "README.md"
    if not os.path.exists(readme_path):
        print("README.md not found in repo root.", file=sys.stderr)
        sys.exit(1)

    with open(readme_path, "r", encoding="utf-8") as f:
        text = f.read()

    pattern = re.compile(r"(<!--START_TOTAL_SCORE-->)(.*?)(<!--END_TOTAL_SCORE-->)", re.S)
    replacement = r"\1{}\3".format(total)

    if not pattern.search(text):
        print("Placeholder <!--START_TOTAL_SCORE-->...<!--END_TOTAL_SCORE--> not found in README.md", file=sys.stderr)
        sys.exit(1)

    new_text = pattern.sub(replacement, text, count=1)

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(new_text)

    print(f"Updated README.md: total (stars+forks) = {total}")

def main():
    try:
        user = get_authenticated_user()
        if not user:
            print("Failed to get authenticated user.", file=sys.stderr)
            sys.exit(1)
        print(f"Authenticated as: {user}")

        repos = fetch_all_repos(user)
        print(f"Fetched {len(repos)} repositories (owned by {user}).")

        total, stars, forks = calculate_total_score(repos)
        print(f"stars: {stars}, forks: {forks}, total: {total}")

        update_readme(total)

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
