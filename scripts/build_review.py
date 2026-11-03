"""Build the review page (cards, reel, caption per day) from schedule.json.

Usage: python scripts/build_review.py FROM_DATE OUT_HTML TAG
Prints a JSON map {published path: repo path} for the Artifact publish `files`.
Media is published under media/TAG/... so a republish never shows a cached old video.
"""
import datetime, html, json, sys

start, out, tag = sys.argv[1], sys.argv[2], sys.argv[3]
s = json.load(open("schedule.json"))
done = {p["id"] for p in json.load(open("published.json"))}
days = {}
for p in s["posts"]:
    if p["date"] >= start:
        days.setdefault(p["date"], {})[p["type"]] = p
wd = "월화수목금토일"
files = {}


def pub(path):
    k = path.replace("media/", f"media/{tag}/", 1)
    files[k] = path
    return k


def pill(p):
    if p["id"] in done:
        return '<span class="pill done">게시됨</span>'
    if p["approved"]:
        return '<span class="pill ok">승인됨</span>'
    return '<span class="pill wait">점검 대기</span>'


weeks = {}
for d in sorted(days):
    c, r = days[d]["card"], days[d]["reel"]
    dt = datetime.date.fromisoformat(d)
    q = c["caption"].split("\n")[1][3:]
    imgs = "".join(f'<img src="{pub(m)}" alt="{i+1}번째 장" loading="lazy" width="1080" height="1350">' for i, m in enumerate(c["media"]))
    wk = (c["no"] - 1) // 7 + 1
    weeks.setdefault(wk, []).append(f'''<article class="day">
 <header class="dayhead"><span class="no">{c['no']}</span><div><p class="date">{dt.month}/{dt.day}({wd[dt.weekday()]})</p><h2>{html.escape(q)}</h2></div></header>
 <div class="slots">
  <section class="slot"><div class="slothead"><span class="time">12:00</span><span class="kind">카드뉴스 · 메인 피드</span>{pill(c)}</div><div class="carousel">{imgs}</div></section>
  <section class="slot"><div class="slothead"><span class="time">20:00</span><span class="kind">릴스 · 릴스 탭만</span>{pill(r)}</div><video src="{pub(r['media'][0])}" controls playsinline preload="metadata"></video></section>
 </div>
 <details class="cap"><summary>캡션 보기 (카드뉴스·릴스 공통)</summary><pre>{html.escape(c['caption'])}</pre></details>
</article>''')

body = ""
for wk, arts in sorted(weeks.items(), reverse=True):
    body += f'<section class="week"><h3>{wk}주차</h3>{"".join(arts)}</section>'

css = open(__file__.replace("build_review.py", "review.css")).read()
page = f'''<title>스피드랙 인스타 업로드 점검</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;600&family=Noto+Sans+KR:wght@800;900&display=swap">
<style>{css}</style>
<div class="wrap">
<header class="top"><h1><b>@speedrack_official</b> 업로드 점검</h1>
<p>날짜마다 12:00 카드뉴스(메인 피드)와 20:00 릴스(릴스 탭)가 같은 주제로 올라가요. '점검 대기'인 게시물은 승인해 주시기 전까지 올라가지 않아요. 캡션은 '캡션 보기'를 누르면 펼쳐져요.</p></header>
{body}
</div>'''
open(out, "w").write(page)
print(json.dumps(files))
