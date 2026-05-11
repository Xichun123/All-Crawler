# crawler-analysis

Cross-platform descriptive analysis of short-video interaction metrics
(likes / comments count / shares) crawled from Bilibili, Douyin, Kuaishou,
Weibo, Xhs. Compares AI-generated content against human-made content
side-by-side, where the AI/non-AI judgement is supplied manually.

## 当前阶段说明

当前阶段只分析**视频互动指标**:点赞数、评论数、分享数。推荐优先使用各平台爬虫的 **creator 模式**输出,因为它通常覆盖同一作者/账号下的一批视频,适合做横向描述统计。

`detail` 模式也可以被 loader 读取,但当前报告会忽略评论正文,只使用每条视频的互动计数字段。如果同时放入 creator 和 detail 文件,工具会按 `url` 去重,避免同一视频重复计入。

后续阶段计划基于 `detail` 模式中的评论列表做 NLP 分析,例如评论情感分析、主题聚类或关键词提取。届时应单独扩展评论 schema / loader / report,不要和当前的视频级互动指标统计混在一起。

## Layout

```
Analysis/
├── analyze.py                 # one-shot entrypoint
├── crawler_analysis/          # the reusable package
│   ├── schema.py              # Video dataclass + canonical columns
│   ├── loaders/               # one file per platform
│   │   ├── base.py
│   │   └── douyin.py
│   ├── labeling.py            # CSV template + merge
│   └── stats.py               # describe + AI-vs-Human + charts
├── data/{platform}/*.json     # raw crawler output (gitignored)
├── labels/{platform}.csv      # human-edited AI/non-AI labels
└── reports/                   # generated markdown + PNG (gitignored)
```

## Usage

```bash
pip install -r requirements.txt

# 1. Drop crawler JSON into data/<platform>/
# 2. Generate label templates and an initial report:
python analyze.py --refresh-labels

# 3. Open labels/<platform>.csv, fill the is_ai column (1 / 0).
# 4. Re-run to regenerate the report with labels applied:
python analyze.py
```

`labels/<platform>.csv` columns: `url, is_ai, note, title, author`.
`is_ai` accepts `1/0`, `true/false`, `yes/no`, `ai/human`, or empty
(unlabeled).

## Adding a new platform

1. Implement `crawler_analysis/loaders/<platform>.py` subclassing
   `BaseLoader`. Set `platform = "<name>"` and implement
   `load_file(path) -> Iterable[Video]`.
2. Register it in `crawler_analysis/loaders/__init__.py`.
3. Drop crawler files into `data/<name>/` and run `analyze.py`.

The schema is intentionally narrow — `likes / comments / shares` are
the only required metrics. `collects` is optional (Douyin has it,
others may not).

## Output

- `reports/report.md` — descriptive stats, label coverage, AI-vs-Human
  median ratio.
- `reports/charts/median_<metric>.png` — bar chart per metric.
- `reports/charts/box_<metric>.png` — distribution per
  (platform, AI/Human/Unlabeled) group, symlog scale.

This tool only does **descriptive** statistics. No hypothesis tests,
no inference. Read the medians, eyeball the boxplots.
