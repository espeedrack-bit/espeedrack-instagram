"""Publish scheduled card-news carousels and reels to Instagram via the Graph API.

Usage:
  python scripts/publish.py                 # post whatever is due for the current KST slot
  python scripts/publish.py --id ID         # post one specific entry now
  python scripts/publish.py --check ID      # build the media container only (nothing goes public)
"""
import argparse, datetime, json, os, sys, time, urllib.parse, urllib.request

API = "https://graph.instagram.com/v21.0"
KST = datetime.timezone(datetime.timedelta(hours=9))
TOKEN = os.environ["IG_ACCESS_TOKEN"]
USER = os.environ["IG_USER_ID"]
REPO = os.environ.get("GITHUB_REPOSITORY", "seyoungk3030-dotcom/speedrack-instagram")
REF = os.environ.get("MEDIA_REF") or os.environ.get("GITHUB_SHA") or "main"


def call(method, path, **params):
    params["access_token"] = TOKEN
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        req = urllib.request.Request(f"{url}?{data.decode()}")
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == 3:
                sys.exit(f"{method} {path} failed: {e.code} {e.read().decode()}")
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            # A container can be published only once, so retrying is safe.
            if attempt == 3:
                sys.exit(f"{method} {path} failed: {e}")
        time.sleep(5 * 2 ** attempt)


def media_url(path):
    return f"https://raw.githubusercontent.com/{REPO}/{REF}/{path}"


def wait_ready(cid, limit=600):
    for _ in range(limit // 10):
        st = call("GET", cid, fields="status_code,status")
        if st.get("status_code") == "FINISHED":
            return
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            sys.exit(f"container {cid} failed: {st}")
        time.sleep(10)
    sys.exit(f"container {cid} not ready after {limit}s")


def build(post):
    if post["type"] == "card":
        children = []
        for m in post["media"]:
            c = call("POST", f"{USER}/media", image_url=media_url(m), is_carousel_item="true")
            wait_ready(c["id"])
            children.append(c["id"])
        cid = call("POST", f"{USER}/media", media_type="CAROUSEL",
                   children=",".join(children), caption=post["caption"])["id"]
    else:
        cid = call("POST", f"{USER}/media", media_type="REELS", video_url=media_url(post["media"][0]),
                   caption=post["caption"], share_to_feed="false")["id"]
    wait_ready(cid)
    return cid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id")
    ap.add_argument("--check")
    a = ap.parse_args()

    sched = json.load(open("schedule.json"))
    published = json.load(open("published.json"))
    done = {p["id"] for p in published}
    by_id = {p["id"]: p for p in sched["posts"]}

    if a.check:
        cid = build(by_id[a.check])
        print(f"container {cid} ready; not published")
        return

    if a.id:
        due = [by_id[a.id]]
    else:
        now = datetime.datetime.now(KST)
        slot = "12:00" if now.hour < 16 else "20:00"
        due = [p for p in sched["posts"] if p["date"] == now.strftime("%Y-%m-%d") and p["slot"] == slot]

    for post in due:
        if not post.get("approved"):
            print(f"{post['id']} is not approved yet; skipped")
            continue
        if post["id"] in done:
            print(f"{post['id']} already published")
            continue
        cid = build(post)
        mid = call("POST", f"{USER}/media_publish", creation_id=cid)["id"]
        link = call("GET", mid, fields="permalink").get("permalink")
        print(f"published {post['id']} -> {link}")
        published.append({"id": post["id"], "media_id": mid, "permalink": link,
                          "at": datetime.datetime.now(KST).isoformat(timespec="seconds")})
        json.dump(published, open("published.json", "w"), ensure_ascii=False, indent=1)
    if not due:
        print("nothing due for this slot")


if __name__ == "__main__":
    main()
