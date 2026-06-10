import os
import sys
import argparse
import subprocess
import json
import re
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

def main():
    parser = argparse.ArgumentParser(description="Fetch Weibo feeds for Zhang Linghe digest")
    parser.add_argument("--whitelist", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "whitelist-zlh.json"), help="Path to whitelist json")
    parser.add_argument("--date", help="Date to filter posts (YYYY-MM-DD), default is yesterday")
    parser.add_argument("--column", help="Filter by whitelist column (e.g. 官方组)")
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
        print("Error: mcporter not found. Please install it: npm install -g mcporter", file=sys.stderr)
        sys.exit(1)

    all_posts = []

    for idx, acc in enumerate(accounts, 1):
        uid = acc.get("uid")
        name = acc.get("screen_name")
        col = acc.get("column")
        role = acc.get("role")

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

            for post in data:
                created_at_raw = post.get("created_at", "")
                post_date, post_time = parse_weibo_date(created_at_raw)

                if post_date == args.date:
                    cleaned_text = clean_weibo_text(post.get("text", ""))
                    attitudes = post.get("attitudes_count", 0) or 0
                    reposts = post.get("reposts_count", 0) or 0
                    comments = post.get("comments_count", 0) or 0
                    engagement = attitudes + reposts + 0.5 * comments

                    all_posts.append({
                        "id": post.get("id"),
                        "author": post.get("user", {}).get("screen_name", name),
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
                        "url": f"https://weibo.com/{uid}/{post.get('id')}"
                    })
        except subprocess.TimeoutExpired:
            print(f"Warning: Timeout fetching feeds for {name} ({uid})", file=sys.stderr)
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON response for {name} ({uid})", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Failed to fetch feeds for {name} ({uid}): {e}", file=sys.stderr)

    all_posts.sort(key=lambda x: x["time"] or "", reverse=True)
    print(json.dumps(all_posts, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()