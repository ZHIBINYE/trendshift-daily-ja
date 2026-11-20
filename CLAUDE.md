# trendshift-daily-ja

trendshift.io の daily ランキング（GitHub トレンド上位 25 件）を毎日取得し、
日本語の解説つき一覧＋詳細ページ（`docs/index.html`）を生成するリポジトリ。

## 構成

- `scripts/fetch_ranking.py` — ランキング取得 → `data/daily/YYYY-MM-DD.json`。解説が未作成のリポジトリを表示
- `data/repos/{owner}__{repo}.json` — リポジトリごとの日本語解説（書き方は `ANALYSIS_GUIDE.md`）
- `scripts/build_site.py` — `docs/index.html`（ローカル/GitHub Pages 用）と `dist/artifact.html`（Artifact 用）を生成
- `scripts/template.html` — ページのテンプレート（データは `__DATA__` に埋め込まれる）

## 毎日の更新手順

1. `python3 scripts/fetch_ranking.py`
2. 表示された「missing analysis」の各リポジトリについて、`ANALYSIS_GUIDE.md` に従い `data/repos/{owner}__{repo}.json` を作成する
   （既に解説があるリポジトリは作り直さない。`analyzed_at` が 60 日以上前のものだけは README を読み直して更新してよい）
3. `python3 scripts/build_site.py` を実行し、`invalid analysis JSON` や `latest day missing analysis` が出ないことを確認する
4. `git add data docs dist && git commit -m "daily: YYYY-MM-DD" && git push`

trendshift がまだ前日のデータのまま（`data/daily/` に同じ日付が既にあり内容も同じ）なら、何もコミットせず終了してよい。
