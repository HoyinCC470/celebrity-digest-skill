import os
import sys
import argparse
import json
import re
import subprocess
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

def clean_weibo_text(html: str) -> str:
    if not html:
        return ""
    s = re.sub(r'<br\s*/?>', '\n', html)
    s = re.sub(r'<a [^>]*>([^<]*)</a>', r'\1', s)
    s = re.sub(r'<[^>]+>', '', s)
    return s.strip()

def parse_weibo_date(date_str):
    try:
        dt = datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")
    except Exception:
        return None, None

def fetch_via_jina(url: str) -> dict:
    jina_url = f"https://r.jina.ai/{url}"
    req = urllib.request.Request(jina_url, headers={
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/plain"
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        text = resp.read().decode("utf-8")
    content_marker = "Markdown Content:\n"
    idx = text.find(content_marker)
    if idx == -1:
        return {}
    json_text = text[idx + len(content_marker):]
    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        return {}

def get_container_id(uid: int) -> str:
    return f"107603{uid}"

def fetch_feeds_jina(uid: int, limit: int = 15) -> list:
    container_id = get_container_id(uid)
    url = f"https://m.weibo.cn/api/container/getIndex?type=uid&value={uid}&containerid={container_id}"
    data = fetch_via_jina(url)
    if not data:
        return []
    cards = data.get("data", {}).get("cards", [])
    posts = []
    for card in cards:
        mblog = card.get("mblog")
        if not mblog:
            continue
        posts.append(mblog)
        if len(posts) >= limit:
            break
    return posts

def fetch_profile_jina(uid: int) -> dict:
    url = f"https://m.weibo.cn/api/container/getIndex?type=uid&value={uid}"
    data = fetch_via_jina(url)
    if not data:
        return {}
    return data.get("data", {}).get("userInfo", {})

def main():
    parser = argparse.ArgumentParser(description="Fetch Weibo feeds for Zhang Linghe digest")
    parser.add_argument("--whitelist", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "whitelist-zlh.json"), help="Path to whitelist json")
    parser.add_argument("--date", help="Date to filter posts (YYYY-MM-DD), default is yesterday")
    parser.add_argument("--column", help="Filter by whitelist column (e.g. 官方组)")
    parser.add_argument("--method", choices=["jina", "mcporter"], default="jina", help="Fetch method: jina (default, no login needed) or mcporter")
    args = parser.parse_args()

    if not args.date:
        yesterday = datetime.now() - timedelta(days=1)
        args.date = yesterday.strftime("%Y-%m-%d")

    if not os.path.exists(args.whitelist):
        print(f"Error: Whitelist file not found at {args.whitelist}", file=sys.stderr)
        sys.exit(1)

    with open(args.whitelist, "r", encoding="utf-8") as f:
        whitelist_data = json.load(f)

    accounts = whitelist_data.get("accounts", [])
    if args.column:
        accounts = [acc for acc in accounts if acc.get("column") == args.column]

    if not accounts:
        if args.column:
            print(f"No accounts found for column: {args.column}", file=sys.stderr)
        else:
            print("No accounts found in whitelist", file=sys.stderr)
        print("[]")
        return

    all_posts = []
    method = args.method

    if method == "mcporter":
        mcporter_cmd = None
        for candidate in ["mcporter"]:
            try:
                result = subprocess.run([candidate, "--version"], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    mcporter_cmd = candidate
                    break
            except Exception:
                continue

        if not mcporter_cmd:
            print("Error: mcporter not found. Use --method jina instead, or install mcporter: npm install -g mcporter", file=sys.stderr)
            sys.exit(1)

    for idx, acc in enumerate(accounts, 1):
        uid = acc.get("uid")
        name = acc.get("screen_name")
        col = acc.get("column")
        role = acc.get("role")

        if idx > 1:
            import time
            time.sleep(3)

        raw_posts = []

        if method == "jina":
            try:
                print(f"Fetching {name} ({uid}) via Jina Reader... ({idx}/{len(accounts)})", file=sys.stderr)
                raw_posts = fetch_feeds_jina(uid, limit=15)
                if not raw_posts:
                    print(f"Warning: No posts returned for {name} ({uid})", file=sys.stderr)
            except Exception as e:
                print(f"Warning: Failed to fetch feeds for {name} ({uid}): {e}", file=sys.stderr)
                continue

        elif method == "mcporter":
            if idx > 1:
                import time
                time.sleep(10)

            cmd = [mcporter_cmd, "call", f"weibo.get_feeds(uid: {uid}, limit: 15)"]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if res.returncode != 0:
                    print(f"Warning: mcporter returned non-zero for {name} ({uid}): {res.stderr}", file=sys.stderr)
                    continue
                data = json.loads(res.stdout)
                if not isinstance(data, list):
                    print(f"Warning: Unexpected response format for {name} ({uid})", file=sys.stderr)
                    continue
                raw_posts = data
            except subprocess.TimeoutExpired:
                print(f"Warning: Timeout fetching feeds for {name} ({uid})", file=sys.stderr)
            except json.JSONDecodeError:
                print(f"Warning: Invalid JSON response for {name} ({uid})", file=sys.stderr)
            except Exception as e:
                print(f"Warning: Failed to fetch feeds for {name} ({uid}): {e}", file=sys.stderr)
                continue

        for post in raw_posts:
            if isinstance(post, dict):
                created_at_raw = post.get("created_at", "")
            else:
                continue

            post_date, post_time = parse_weibo_date(created_at_raw)

            if method == "jina":
                if not post_date:
                    created_ts = post.get("created_at_timestamp", 0)
                    if created_ts:
                        dt = datetime.fromtimestamp(created_ts)
                        post_date = dt.strftime("%Y-%m-%d")
                        post_time = dt.strftime("%H:%M")

            if post_date == args.date:
                text_field = post.get("text", post.get("mblog_text", ""))
                cleaned_text = clean_weibo_text(text_field)

                if method == "jina":
                    attitudes = post.get("attitudes_count", post.get("like_count", 0)) or 0
                    reposts = post.get("reposts_count", 0) or 0
                    comments = post.get("comments_count", 0) or 0
                    post_id = post.get("id", post.get("mid", ""))
                    post_id_str = str(post_id)
                    user_info = post.get("user", {})
                    if isinstance(user_info, dict):
                        user_id = user_info.get("id", uid)
                        author_name = user_info.get("screen_name", name)
                    else:
                        user_id = uid
                        author_name = name
                    url = f"https://weibo.com/{user_id}/{post_id_str}"
                else:
                    cleaned_text = clean_weibo_text(post.get("text", ""))
                    attitudes = post.get("attitudes_count", 0) or 0
                    reposts = post.get("reposts_count", 0) or 0
                    comments = post.get("comments_count", 0) or 0
                    post_id = post.get("id", "")
                    url = f"https://weibo.com/{uid}/{post_id}"
                    author_name = post.get("user", {}).get("screen_name", name) if isinstance(post.get("user"), dict) else name

                engagement = attitudes + reposts + 0.5 * comments

                all_posts.append({
                    "id": post_id if method == "jina" else post.get("id"),
                    "author": author_name,
                    "uid": uid,
                    "column": col,
                    "role": role,
                    "raw_time": created_at_raw,
                    "date": post_date,
                    "time": post_time,
                    "text": cleaned_text,
                    "attitudes_count": attitudes,
                    "reposts_count": reposts,
                    "comments_count": comments,
                    "engagement_score": engagement,
                    "url": url
                })

    all_posts.sort(key=lambda x: x["time"] or "", reverse=True)
    print(json.dumps(all_posts, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()