#!/usr/bin/env python3
"""data/ から一覧＋詳細ページ（1ファイルの HTML、ハッシュで画面切替）を生成する。

出力:
  docs/index.html      ローカル閲覧・GitHub Pages 用（完全な HTML 文書）
  dist/artifact.html   claude.ai Artifact 公開用（<head>/<body> を含まない本文のみ）
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEEP_DAYS = 30  # ページに埋め込む直近の日数

REQUIRED = ["title_ja", "category", "summary_ja", "features", "how_to_use", "effects", "domains", "cautions"]


def load():
    daily_files = sorted((ROOT / "data" / "daily").glob("*.json"), reverse=True)[:KEEP_DAYS]
    days = [json.loads(p.read_text(encoding="utf-8")) for p in daily_files]
    slugs = {it["slug"] for d in days for it in d["items"]}
    repos, broken = {}, []
    for s in sorted(slugs):
        p = ROOT / "data" / "repos" / f"{s}.json"
        if not p.exists():
            continue
        try:
            a = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            broken.append(s)
            continue
        if any(k not in a for k in REQUIRED):
            broken.append(s)
            continue
        repos[s] = a
    return days, repos, slugs, broken


def main():
    days, repos, slugs, broken = load()
    if not days:
        raise SystemExit("data/daily にランキングがありません。先に fetch_ranking.py を実行してください")

    jst = timezone(timedelta(hours=9))
    data = {
        "generated_at": datetime.now(jst).strftime("%Y-%m-%d %H:%M JST"),
        "days": [{"date": d["date"], "items": d["items"]} for d in days],
        "repos": repos,
    }
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    body = (ROOT / "scripts" / "template.html").read_text(encoding="utf-8").replace("__DATA__", blob)

    dist = ROOT / "dist" / "artifact.html"
    dist.parent.mkdir(exist_ok=True)
    dist.write_text(body, encoding="utf-8")

    head, rest = body.split("</style>", 1)
    full = ('<!doctype html>\n<html lang="ja">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f"{head}</style>\n</head>\n<body>\n{rest}</body>\n</html>\n")
    docs = ROOT / "docs" / "index.html"
    docs.parent.mkdir(exist_ok=True)
    docs.write_text(full, encoding="utf-8")

    latest = {it["slug"] for it in days[0]["items"]}
    missing = sorted(latest - set(repos))
    print(f"built: {docs.relative_to(ROOT)}, {dist.relative_to(ROOT)} "
          f"({len(days)} days, {len(repos)}/{len(slugs)} repos analyzed, {len(body)//1024} KB)")
    if broken:
        print("invalid analysis JSON:", ", ".join(broken))
    if missing:
        print("latest day missing analysis:", ", ".join(missing))


if __name__ == "__main__":
    main()
