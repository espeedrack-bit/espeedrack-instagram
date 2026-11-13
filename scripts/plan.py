"""Build schedule.json for the new accounts (Instagram espeedrack + YouTube 스피드랙온라인지점).

All 151 v4 FAQs are posted from scratch in ORDER.
  Instagram: one FAQ a day, 12:00 card-news carousel + 20:00 reel of the same FAQ.
  YouTube:   the same reels as Shorts, YT_FIRST_PER_DAY a day for YT_RAMP_DAYS days, then YT_LATER_PER_DAY.

Usage:
  python scripts/plan.py --ig-start 2026-11-16 --yt-start 2026-11-16 [--bank faq-bank.xlsx]
Captions come from the FAQ bank (질문 + 답변). Every post starts with approved=false;
weeks are approved with SY before they go out.
"""
import argparse, datetime, json, re

ORDER = [
    1, 13, 15, 17, 19, 21, 27,            # week 1 (top asked)
    4, 6, 8, 10, 12, 14, 18,
    20, 22, 24, 26, 28, 29, 30,
    2, 3, 5, 7, 9, 11, 16,
    23, 25, 32, 33, 34, 35, 36,
    37, 38, 39, 41, 43, 44, 45,
    46, 47, 48, 49, 50, 51, 52,
    53, 54, 59, 60, 62, 63, 65,
    68, 70, 71, 72, 77, 79, 81,
    82, 86, 94, 95, 99, 101, 103,
    108, 111, 112, 126, 127, 132, 135,
    85, 107, 133, 138, 139, 140, 144,
    145, 150, 153, 155, 159, 162, 171,
    165, 176, 179, 184, 189, 182, 183,
    180, 185, 187, 190, 191, 193, 194,
    199, 200, 202, 204, 205, 211, 213,
    214, 221, 222, 227, 239, 245, 247,
    251, 257, 267, 282, 283, 286, 301,
    323, 333, 334, 341, 343, 344, 358,
    366, 373, 374, 383, 408, 420, 424,
    426, 428, 455, 460, 469, 493, 496,
    485, 521, 541, 566,
]
assert len(ORDER) == len(set(ORDER)) == 151

YT_SLOTS = {3: ["09:00", "14:00", "20:00"],
            6: ["08:00", "10:00", "12:00", "15:00", "18:00", "21:00"]}
YT_FIRST_PER_DAY, YT_RAMP_DAYS, YT_LATER_PER_DAY = 3, 14, 6

TAGS = "#스피드랙 #스피드랙선반 #조립식선반 #수납선반 #정리정돈 #수납정리 #자주묻는질문"
OUTRO = "스피드랙을 고민 중이거나 이미 쓰고 계신 고객님들이 자주 물어보신 질문이에요. 더 궁금한 점은 댓글로 남겨 주세요."


def load_bank(path):
    import openpyxl
    ws = openpyxl.load_workbook(path, read_only=True).worksheets[0]
    rows = ws.iter_rows(values_only=True)
    head = next(rows)
    iq, ia, ino = head.index("질문"), head.index("답변"), head.index("번호")
    return {int(r[ino]): (str(r[iq]).strip(), str(r[ia]).strip()) for r in rows if r[ino]}


def caption(q, a):
    return f"[스피드랙 자주 묻는 질문]\nQ. {q}\n\n{a}\n\n{OUTRO}\n\n{TAGS}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ig-start", required=True)
    ap.add_argument("--yt-start", required=True)
    ap.add_argument("--bank", default="/mnt/project-files/faq-cardnews/faq-bank.xlsx")
    a = ap.parse_args()
    bank = load_bank(a.bank)
    d0 = datetime.date.fromisoformat(a.ig_start)
    posts, yt = [], []
    for i, n in enumerate(ORDER):
        q, ans = bank[n]
        cap = caption(q, ans)
        d = (d0 + datetime.timedelta(days=i)).isoformat()
        base = {"faq": n, "no": i + 1, "caption": cap, "approved": False}
        posts.append({"id": f"{d}-1200-faq{n}", "date": d, "slot": "12:00", "type": "card",
                      "media": [f"media/cards/FAQ{n:03d}_{k}.jpg" for k in range(1, 7)], **base})
        posts.append({"id": f"{d}-2000-faq{n}", "date": d, "slot": "20:00", "type": "reel",
                      "media": [f"media/reels/reel_{n}.mp4"], **base})
    day, k = datetime.date.fromisoformat(a.yt_start), 0
    while k < len(ORDER):
        per = YT_FIRST_PER_DAY if (day - datetime.date.fromisoformat(a.yt_start)).days < YT_RAMP_DAYS else YT_LATER_PER_DAY
        for slot in YT_SLOTS[per]:
            if k == len(ORDER):
                break
            n = ORDER[k]
            q, ans = bank[n]
            yt.append({"id": f"yt-{day.isoformat()}-{slot.replace(':', '')}-faq{n}", "date": day.isoformat(),
                       "slot": slot, "type": "short", "faq": n, "no": k + 1, "question": q,
                       "media": [f"media/reels/reel_{n}.mp4"], "caption": caption(q, ans), "approved": False})
            k += 1
        day += datetime.timedelta(days=1)
    json.dump({"posts": posts, "youtube": yt}, open("schedule.json", "w"), ensure_ascii=False, indent=1)
    print(f"instagram {posts[0]['date']}..{posts[-1]['date']} ({len(posts)} posts); "
          f"youtube {yt[0]['date']}..{yt[-1]['date']} ({len(yt)} shorts)")


if __name__ == "__main__":
    main()
