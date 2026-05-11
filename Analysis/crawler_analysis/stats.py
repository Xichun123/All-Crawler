"""Descriptive statistics and AI/non-AI comparison.

Pure pandas — no inferential tests. The point is to *describe* the data:
counts, central tendency, dispersion, and side-by-side AI vs non-AI views
across platforms.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from .schema import Video, VIDEO_COLUMNS


METRICS = ["likes", "comments", "shares"]

METRIC_LABELS = {
    "likes": "点赞数",
    "comments": "评论数",
    "shares": "分享数",
}

AI_GROUP_LABELS = {
    "AI": "AI 内容",
    "Human": "非 AI 内容",
    "Unlabeled": "未标注",
}

PLATFORM_LABELS = {
    "douyin": "抖音",
    "bilibili": "B站",
    "kuaishou": "快手",
    "weibo": "微博",
    "xhs": "小红书",
}

REPORT_COLUMN_LABELS = {
    "platform": "平台",
    "ai_group": "内容类型",
    "metric": "指标",
    "n": "样本数",
    "mean": "均值",
    "median": "中位数",
    "std": "标准差",
    "min": "最小值",
    "p25": "25分位数",
    "p75": "75分位数",
    "max": "最大值",
    "AI": "AI 内容",
    "Human": "非 AI 内容",
    "Unlabeled": "未标注",
    "total": "总数",
    "n_ai": "AI 样本数",
    "n_human": "非 AI 样本数",
    "median_ai": "AI 中位数",
    "median_human": "非 AI 中位数",
    "ratio_ai_over_human": "AI/非 AI 中位数比值",
}


def videos_to_dataframe(videos: Iterable[Video]) -> pd.DataFrame:
    df = pd.DataFrame([v.to_row() for v in videos], columns=VIDEO_COLUMNS)
    for col in METRICS + ["collects"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if "publish_time" in df.columns:
        df["publish_time"] = pd.to_datetime(df["publish_time"], errors="coerce")
    return df


def _ai_group_label(v) -> str:
    if v is True:
        return "AI"
    if v is False:
        return "Human"
    return "Unlabeled"


def describe_by_platform(df: pd.DataFrame) -> pd.DataFrame:
    """Per-platform descriptive stats for likes/comments/shares."""
    rows = []
    for platform, sub in df.groupby("platform"):
        for metric in METRICS:
            s = sub[metric].dropna()
            rows.append(
                {
                    "platform": platform,
                    "metric": metric,
                    "n": int(s.shape[0]),
                    "mean": float(s.mean()) if len(s) else float("nan"),
                    "median": float(s.median()) if len(s) else float("nan"),
                    "std": float(s.std(ddof=1)) if len(s) > 1 else float("nan"),
                    "min": float(s.min()) if len(s) else float("nan"),
                    "p25": float(s.quantile(0.25)) if len(s) else float("nan"),
                    "p75": float(s.quantile(0.75)) if len(s) else float("nan"),
                    "max": float(s.max()) if len(s) else float("nan"),
                }
            )
    return pd.DataFrame(rows)


def describe_by_platform_ai(df: pd.DataFrame) -> pd.DataFrame:
    """Per-(platform, AI/Human/Unlabeled) descriptive stats."""
    df = df.copy()
    df["ai_group"] = df["is_ai"].apply(_ai_group_label)
    rows = []
    for (platform, group), sub in df.groupby(["platform", "ai_group"]):
        for metric in METRICS:
            s = sub[metric].dropna()
            rows.append(
                {
                    "platform": platform,
                    "ai_group": group,
                    "metric": metric,
                    "n": int(s.shape[0]),
                    "mean": float(s.mean()) if len(s) else float("nan"),
                    "median": float(s.median()) if len(s) else float("nan"),
                    "std": float(s.std(ddof=1)) if len(s) > 1 else float("nan"),
                    "min": float(s.min()) if len(s) else float("nan"),
                    "p25": float(s.quantile(0.25)) if len(s) else float("nan"),
                    "p75": float(s.quantile(0.75)) if len(s) else float("nan"),
                    "max": float(s.max()) if len(s) else float("nan"),
                }
            )
    return pd.DataFrame(rows)


def ai_vs_human_ratio(df: pd.DataFrame) -> pd.DataFrame:
    """For each (platform, metric), median ratio of AI vs Human group.

    Ratio is ``median(AI) / median(Human)`` — values > 1 mean AI videos
    score higher on that metric. NaN if either group is missing or has
    median zero.
    """
    df = df.copy()
    df["ai_group"] = df["is_ai"].apply(_ai_group_label)
    rows = []
    for platform, sub in df.groupby("platform"):
        for metric in METRICS:
            ai = sub.loc[sub["ai_group"] == "AI", metric].dropna()
            hu = sub.loc[sub["ai_group"] == "Human", metric].dropna()
            ai_med = float(ai.median()) if len(ai) else float("nan")
            hu_med = float(hu.median()) if len(hu) else float("nan")
            ratio = ai_med / hu_med if hu_med else float("nan")
            rows.append(
                {
                    "platform": platform,
                    "metric": metric,
                    "n_ai": int(len(ai)),
                    "n_human": int(len(hu)),
                    "median_ai": ai_med,
                    "median_human": hu_med,
                    "ratio_ai_over_human": ratio,
                }
            )
    return pd.DataFrame(rows)


def label_coverage(df: pd.DataFrame) -> pd.DataFrame:
    """How many videos per platform are labeled vs not."""
    df = df.copy()
    df["ai_group"] = df["is_ai"].apply(_ai_group_label)
    pivot = (
        df.pivot_table(
            index="platform",
            columns="ai_group",
            values="video_id",
            aggfunc="count",
            fill_value=0,
        )
        .reset_index()
    )
    for col in ("AI", "Human", "Unlabeled"):
        if col not in pivot.columns:
            pivot[col] = 0
    pivot["total"] = pivot[["AI", "Human", "Unlabeled"]].sum(axis=1)
    return pivot[["platform", "AI", "Human", "Unlabeled", "total"]]


def render_charts(df: pd.DataFrame, out_dir: Path) -> list[Path]:
    """Render comparison charts. Returns list of file paths written."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.font_manager as fm
    import matplotlib.pyplot as plt

    chinese_font_candidates = [
        "PingFang SC",
        "Songti SC",
        "Heiti SC",
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Arial Unicode MS",
    ]
    installed_fonts = {f.name for f in fm.fontManager.ttflist}
    for font in chinese_font_candidates:
        if font in installed_fonts:
            plt.rcParams["font.sans-serif"] = [font]
            break
    plt.rcParams["axes.unicode_minus"] = False

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = df.copy()
    df["ai_group"] = df["is_ai"].apply(_ai_group_label)
    df["ai_group_cn"] = df["ai_group"].map(AI_GROUP_LABELS)
    df["platform_cn"] = df["platform"].map(PLATFORM_LABELS).fillna(df["platform"])

    written: list[Path] = []

    # Median bar chart per metric: platform on x, grouped by ai_group
    for metric in METRICS:
        metric_cn = METRIC_LABELS[metric]
        agg = (
            df.groupby(["platform_cn", "ai_group_cn"])[metric]
            .median()
            .unstack("ai_group_cn")
            .reindex(columns=["AI 内容", "非 AI 内容", "未标注"])
        )
        fig, ax = plt.subplots(figsize=(8, 5))
        agg.plot(kind="bar", ax=ax)
        ax.set_title(f"每条视频{metric_cn}中位数：AI 与非 AI 对比")
        ax.set_ylabel(f"{metric_cn}中位数")
        ax.set_xlabel("平台")
        ax.legend(title="内容类型")
        ax.tick_params(axis="x", rotation=0)
        fig.tight_layout()
        path = out_dir / f"median_{metric}.png"
        fig.savefig(path, dpi=140)
        plt.close(fig)
        written.append(path)

    # Box plot of distribution per metric
    for metric in METRICS:
        metric_cn = METRIC_LABELS[metric]
        groups: list[tuple[str, "pd.Series"]] = []
        for (platform, group), sub in df.groupby(["platform_cn", "ai_group_cn"]):
            s = sub[metric].dropna()
            if len(s) == 0:
                continue
            groups.append((f"{platform}\n{group}", s))
        if not groups:
            continue
        fig, ax = plt.subplots(figsize=(max(6, len(groups) * 1.2), 5))
        ax.boxplot([s.values for _, s in groups], labels=[lbl for lbl, _ in groups])
        ax.set_title(f"{metric_cn}分布")
        ax.set_ylabel(metric_cn)
        ax.set_yscale("symlog")
        fig.tight_layout()
        path = out_dir / f"box_{metric}.png"
        fig.savefig(path, dpi=140)
        plt.close(fig)
        written.append(path)

    return written


def _localize_report_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "platform" in df.columns:
        df["platform"] = df["platform"].map(PLATFORM_LABELS).fillna(df["platform"])
    if "metric" in df.columns:
        df["metric"] = df["metric"].map(METRIC_LABELS).fillna(df["metric"])
    if "ai_group" in df.columns:
        df["ai_group"] = df["ai_group"].map(AI_GROUP_LABELS).fillna(df["ai_group"])
    df = df.rename(columns=REPORT_COLUMN_LABELS)
    return df


def _md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_(空)_"
    return _localize_report_df(df).to_markdown(index=False, floatfmt=".2f")


def _chart_title_cn(stem: str) -> str:
    for metric, label in METRIC_LABELS.items():
        if stem == f"median_{metric}":
            return f"每条视频{label}中位数：AI 与非 AI 对比"
        if stem == f"box_{metric}":
            return f"{label}分布"
    return stem


def render_report(
    df: pd.DataFrame,
    out_path: Path,
    *,
    chart_paths: list[Path] | None = None,
) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    coverage = label_coverage(df)
    by_plat = describe_by_platform(df)
    by_plat_ai = describe_by_platform_ai(df)
    ratio = ai_vs_human_ratio(df)

    platform_names = [
        PLATFORM_LABELS.get(p, p) for p in sorted(df["platform"].unique())
    ]

    parts = ["# 跨平台视频互动指标描述性分析\n"]
    parts.append(
        f"视频总数: **{len(df)}**, 平台: {', '.join(platform_names)}\n"
    )
    parts.append(
        "\n当前报告只分析视频级互动指标:点赞数、评论数、分享数。"
        "数据源优先使用 creator 模式;detail 模式中的评论正文暂不参与本报告,"
        "后续评论内容的 NLP 情感分析会单独处理。\n"
    )

    parts.append("\n## 标注覆盖情况\n")
    parts.append(_md_table(coverage))

    parts.append("\n\n## 各平台整体描述统计\n")
    parts.append(_md_table(by_plat))

    parts.append("\n\n## 按 AI / 非 AI 分组的描述统计\n")
    parts.append(_md_table(by_plat_ai))

    parts.append("\n\n## AI 与非 AI 中位数对比\n")
    parts.append(
        "比值 > 1 表示 AI 内容在该指标上的中位数更高 "
        "(AI 中位数 / 非 AI 中位数)。当 AI 样本数或非 AI 样本数较小时,"
        "该结果只能作为描述性观察,不应做强结论。\n\n"
    )
    parts.append(_md_table(ratio))

    if chart_paths:
        parts.append("\n\n## 图表\n")
        for p in chart_paths:
            rel = Path(p).resolve().relative_to(out_path.parent.resolve())
            title = _chart_title_cn(p.stem)
            parts.append(f"\n![{title}]({rel})\n")

    out_path.write_text("\n".join(parts), encoding="utf-8")
    return out_path
