#!/usr/bin/env python3
"""trendshift.io の daily ランキングを取得して data/daily/YYYY-MM-DD.json に保存する。

使い方:
  python3 scripts/fetch_ranking.py              # https://trendshift.io/ から取得
  python3 scripts/fetch_ranking.py --html FILE  # 取得済み HTML から解析（curl が使えない環境用）

出力した JSON のパスと、解説（data/repos/*.json）が未作成のリポジトリ一覧を表示する。
"""
import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
URL = "https://trendshift.io/"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"


def slug(full_name: str) -> str:
    return full_name.replace("/", "__")


def fetch_html() -> str:
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8")


def parse_initial_data(html: str) -> list:
    """Next.js の RSC ペイロード内の "initialData":[...] を取り出す。"""
    # RSC ペイロードは JS 文字列としてエスケープされているので、まずエスケープを戻す
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.S)
    payload = "".join(json.loads(f'"{c}"') for c in chunks)
    i = payload.find('"initialData":[')
    if i < 0:
        return []
    start = payload.index("[", i)
    depth, j = 0, start
    in_str = esc = False
    for j in range(start, len(payload)):
        ch = payload[j]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                break
    return json.loads(payload[start : j + 1])


def parse_jsonld(html: str) -> list:
    """フォールバック: JSON-LD の ItemList（星数などは無い）。"""
    for m in re.finditer(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S):
        d = json.loads(m.group(1))
        if d.get("@type") == "ItemList":
            out = []
            for it in d["itemListElement"]:
                item = it["item"]
                out.append({
                    "rank": it["position"],
                    "full_name": item["name"],
                    "repository_id": int(it["url"].rstrip("/").split("/")[-1]),
                    "repository_language": item.get("programmingLanguage"),
                    "repository_description": item.get("description"),
                    "tags": [{"display_name": k} for k in item.get("keywords", [])],
                    "date": item.get("dateModified"),
                })
            return out
    return []


def normalize(items: list) -> list:
    out = []
    for x in items:
        out.append({
            "rank": x["rank"],
            "full_name": x["full_name"],
            "slug": slug(x["full_name"]),
            "github_url": f"https://github.com/{x['full_name']}",
            "trendshift_url": f"https://trendshift.io/repositories/{x['repository_id']}",
            "language": x.get("repository_language") or x.get("language"),
            "description": x.get("repository_description") or "",
            "stars": x.get("repository_stars"),
            "forks": x.get("repository_forks"),
            "stars_gained": x.get("repository_stars_gained"),
            "forks_gained": x.get("repository_forks_gained"),
            "score": x.get("score"),
            "created_at": x.get("repository_created_at"),
            "tags": [t.get("display_name") for t in x.get("tags", []) if t.get("display_name")],
            "social": x.get("social_mention_platforms") or [],
        })
    return sorted(out, key=lambda r: r["rank"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", help="取得済み HTML ファイル")
    args = ap.parse_args()

    html = Path(args.html).read_text(encoding="utf-8") if args.html else fetch_html()
    items = parse_initial_data(html) or parse_jsonld(html)
    if not items:
        sys.exit("ランキングを解析できませんでした（ページ構造が変わった可能性）")

    ranking = normalize(items)
    # trendshift の date は集計日（UTC 00:00）。これをランキング日付とする
    raw_date = (items[0].get("date") or "")[:10]
    if not raw_date:
        sys.exit("ランキング日付を取得できませんでした")

    out = ROOT / "data" / "daily" / f"{raw_date}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"date": raw_date, "source": URL, "items": ranking},
                              ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"saved: {out.relative_to(ROOT)} ({len(ranking)} repos)")

    missing = [r["full_name"] for r in ranking
               if not (ROOT / "data" / "repos" / f"{r['slug']}.json").exists()]
    print(f"missing analysis: {len(missing)}")
    for name in missing:
        print(f"  {name}")


if __name__ == "__main__":
    main()
