"""Upload the day's approved reel to YouTube as a Short (YouTube Data API v3).

Uses the "youtube" list in schedule.json (built by scripts/plan.py; its own pace, separate
from Instagram) and its approval flag, and logs uploads to youtube.json so nothing goes up twice.

Usage:
  python scripts/youtube.py            # upload the reel due for the current KST slot
  python scripts/youtube.py --id ID    # upload one specific reel entry now

Needs repo secrets YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN (scope youtube.upload).
If they are not set, it prints a note and exits without error.
"""
import argparse, datetime, json, os, sys, time, urllib.parse, urllib.request

KST = datetime.timezone(datetime.timedelta(hours=9))
LOG = "youtube.json"
PRIVACY = os.environ.get("YT_PRIVACY") or "public"


def access_token():
    data = urllib.parse.urlencode({
        "client_id": os.environ["YT_CLIENT_ID"],
        "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    with urllib.request.urlopen("https://oauth2.googleapis.com/token", data, timeout=60) as r:
        return json.load(r)["access_token"]


def title_of(post):
    q = post.get("question") or next((l[3:].strip() for l in post["caption"].splitlines() if l.startswith("Q. ")), "")
    t = f"{q} | 스피드랙 자주 묻는 질문 #Shorts"
    return t if len(t) <= 100 else q[:100 - 9] + " #Shorts"


def upload(token, post):
    path = post["media"][0]
    size = os.path.getsize(path)
    meta = {
        "snippet": {
            "title": title_of(post),
            "description": post["caption"] + "\n\n#Shorts",
            "tags": ["스피드랙", "조립식선반", "수납선반", "정리정돈", "자주묻는질문", "Shorts"],
            "categoryId": "26",  # Howto & Style
            "defaultLanguage": "ko",
        },
        "status": {"privacyStatus": PRIVACY, "selfDeclaredMadeForKids": False},
    }
    init = urllib.request.Request(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        data=json.dumps(meta).encode(), method="POST",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json; charset=UTF-8",
                 "X-Upload-Content-Type": "video/mp4",
                 "X-Upload-Content-Length": str(size)})
    with urllib.request.urlopen(init, timeout=60) as r:
        loc = r.headers["Location"]
    for attempt in range(4):
        try:
            req = urllib.request.Request(loc, data=open(path, "rb").read(), method="PUT",
                                         headers={"Authorization": f"Bearer {token}",
                                                  "Content-Type": "video/mp4"})
            with urllib.request.urlopen(req, timeout=600) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == 3:
                sys.exit(f"upload failed: {e.code} {e.read().decode()}")
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            if attempt == 3:
                sys.exit(f"upload failed: {e}")
        time.sleep(5 * 2 ** attempt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id")
    a = ap.parse_args()
    if not all(os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")):
        print("YouTube secrets not set; skipped")
        return

    sched = json.load(open("schedule.json"))
    log = json.load(open(LOG)) if os.path.exists(LOG) else []
    done = {x["id"] for x in log}
    items = sched.get("youtube", [])
    by_id = {p["id"]: p for p in items + sched["posts"]}
    if a.id:
        due = [by_id[a.id]]
    else:
        # Everything scheduled for today whose slot has come (late runs catch up the same day).
        now = datetime.datetime.now(KST)
        due = [p for p in items if p["date"] == now.strftime("%Y-%m-%d") and p["slot"] <= now.strftime("%H:%M")]

    token = None
    for post in due:
        if not post.get("approved"):
            print(f"{post['id']} is not approved yet; skipped")
            continue
        if post["id"] in done:
            print(f"{post['id']} already on YouTube")
            continue
        token = token or access_token()
        v = upload(token, post)
        url = f"https://youtube.com/shorts/{v['id']}"
        print(f"uploaded {post['id']} -> {url} ({v.get('status', {}).get('privacyStatus')})")
        log.append({"id": post["id"], "video_id": v["id"], "url": url,
                    "at": datetime.datetime.now(KST).isoformat(timespec="seconds")})
        json.dump(log, open(LOG, "w"), ensure_ascii=False, indent=1)
    if not due:
        print("no reel due for this slot")


if __name__ == "__main__":
    main()
