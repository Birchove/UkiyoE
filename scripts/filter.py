#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
filter.py —— 浮世微言 · 过滤 / 打标 / 去重 / 看板(② 过滤)

职责:读取 crawl.py 产出的当日候选清单 →
      ① 黑名单过滤(花边 / 政治 / 无意义)
      ② 分类打标(人物 / 时事 / 风物 / 笑语,仅辅助,人工可改)
      ③ 跨源去重(同一话题在多平台登榜 → 合并,聚合各源链接与热度)
      → 输出:
        data/filtered/YYYY-MM-DD.json   机读候选(去重合并后)
        data/board/YYYY-MM-DD.md        「稍微美化」的选题看板(供人工勾选)

纯标准库。用法:
  python3 scripts/filter.py                 # 处理今天
  python3 scripts/filter.py --date 2026-07-22
  python3 scripts/filter.py --similarity 0.7   # 调节去重松紧(0~1,越大越严)

重要:本脚本只做「初筛与整理」,**最终取舍必须由人工**——品味与客观性不能交给机器。
"""

import argparse
import json
import re
import unicodedata
from collections import Counter
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CANDIDATES_DIR = REPO_ROOT / "data" / "candidates"
FILTERED_DIR = REPO_ROOT / "data" / "filtered"
BOARD_DIR = REPO_ROOT / "data" / "board"
BLACKLIST_PATH = REPO_ROOT / "config" / "blacklist.txt"

CST = timezone(timedelta(hours=8))

# 看板分类顺序(与本站四栏一致,外加「其他」兜底)
CAT_ORDER = ["时事", "人物", "风物", "笑语", "其他"]

# 分类关键词(仅辅助打标,命中则覆盖来源默认分类)
HUMOR_KW = ["笑", "哈哈", "段子", "搞笑", "沙雕", "离谱", "笑死", "神评",
            "神回复", "爆笑", "谐音梗", "梗", "逗", "社死", "名场面"]
CUSTOMS_KW = ["习俗", "传统", "方言", "汉字", "流行语", "科普", "古人",
              "非遗", "民俗", "节气", "年味", "传统文化", "冷知识", "历史"]
FIGURES_KW = ["去世", "逝世", "离世", "回应", "道歉", "宣布退役", "夺冠",
              "专访", "自述", "去世", "病逝"]


# ── 黑名单 ───────────────────────────────────────────────────
def load_blacklist(path):
    """返回 (子串关键词列表, [(正则, 原式)] 列表)。"""
    subs, regexes = [], []
    if not path.exists():
        return subs, regexes
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("re:"):
            try:
                regexes.append((re.compile(s[3:]), s))
            except re.error:
                continue
        else:
            subs.append(s)
    return subs, regexes


def hit_blacklist(title, subs, regexes):
    """命中返回命中的模式串,否则返回 None。"""
    low = title.lower()
    for kw in subs:
        if kw.lower() in low:
            return kw
    for rx, raw in regexes:
        if rx.search(title):
            return raw
    return None


# ── 分类打标 ─────────────────────────────────────────────────
def refine_category(item):
    t = item.get("title", "")
    if any(k in t for k in HUMOR_KW):
        return "笑语"
    if any(k in t for k in CUSTOMS_KW):
        return "风物"
    if any(k in t for k in FIGURES_KW):
        return "人物"
    return item.get("category_guess") or "其他"


# ── 标题归一 / 去重 ─────────────────────────────────────────
def norm_title(title):
    s = unicodedata.normalize("NFKC", title or "")
    s = re.sub(r"[#\s　]+", "", s)
    s = re.sub(r"[,。.!?,.!?、:;:;;'\"“”‘’()()]", "", s)
    return s.lower()


def bigrams(s):
    return {s[i:i + 2] for i in range(len(s) - 1)} if len(s) >= 2 else {s}


def similarity(a, b):
    """序列相似度 与 字符二元组 Jaccard 取大——后者更能抓住中文改写/语序调换式重复。"""
    seq = SequenceMatcher(None, a, b).ratio()
    ba, bb = bigrams(a), bigrams(b)
    jac = len(ba & bb) / len(ba | bb) if (ba or bb) else 0.0
    return max(seq, jac)


def cluster(items, threshold):
    """按归一标题相似度把候选聚成簇(贪心,与簇代表比较)。"""
    clusters = []
    for it in items:
        nt = it["_norm"]
        placed = False
        for c in clusters:
            if similarity(nt, c["rep"]) >= threshold:
                c["members"].append(it)
                placed = True
                break
        if not placed:
            clusters.append({"rep": nt, "members": [it]})
    return clusters


def merge_cluster(members):
    rep = max(members, key=lambda m: (m.get("heat", 0), len(m.get("title", ""))))
    cats = Counter(refine_category(m) for m in members)
    times = [m["fetched_at"] for m in members if m.get("fetched_at")]
    srcs = {m["source"] for m in members}
    return {
        "title": rep["title"],
        "category_guess": cats.most_common(1)[0][0],
        "heat_max": max(m.get("heat", 0) for m in members),
        "heat_total": sum(m.get("heat", 0) for m in members),
        "source_count": len(srcs),
        "cross_source": len(srcs) >= 2,
        "sources": [
            {"source": m["source"], "source_label": m["source_label"],
             "url": m.get("url", ""), "title": m["title"],
             "heat": m.get("heat", 0), "rank": m.get("rank", 0),
             "fetched_at": m.get("fetched_at", "")}
            for m in members
        ],
        "first_seen": min(times) if times else "",
        "last_seen": max(times) if times else "",
        "tags": [],
    }


# ── 看板渲染 ─────────────────────────────────────────────────
def fmt_heat(n):
    n = n or 0
    if n >= 100_000_000:
        return f"{n / 100_000_000:.1f}亿"
    if n >= 10_000:
        return f"{n / 10_000:.1f}万"
    return str(n)


def md_escape(s):
    return (s or "").replace("|", "\\|").strip()


def render_board(date_str, candidates, stats):
    L = []
    L.append(f"# 浮世微言 · 选题看板({date_str})\n")
    L.append(f"> 本看板由 `filter.py` 自动生成,**仅供选题参考**;取舍与撰写由人工定夺。\n")

    # 概览
    L.append("## 概览\n")
    L.append(f"- 采集候选:**{stats['raw']}** 条")
    L.append(f"- 黑名单剔除:**{stats['blocked']}** 条"
             + (f"(命中 TOP:{stats['block_top']})" if stats["block_top"] else ""))
    L.append(f"- 去重合并后:**{stats['clusters']}** 个话题")
    L.append(f"- 其中跨源热点:**{stats['cross']}** 个(登上 ≥2 个平台)\n")

    def table(rows):
        out = ["| # | 标题 | 来源 | 热度 | 链接 |",
               "|---:|------|------|-----:|------|"]
        for i, c in enumerate(rows, 1):
            srcs = "、".join(
                f"{s['source_label']}" for s in
                sorted(c["sources"], key=lambda x: -x["heat"]))
            links = " ".join(
                f"[{s['source_label']}]({s['url']})" for s in c["sources"] if s["url"])
            out.append(
                f"| {i} | {md_escape(c['title'])} | {md_escape(srcs)} | "
                f"{fmt_heat(c['heat_max'])} | {links or '—'} |")
        return "\n".join(out)

    # 跨源热点优先
    cross = [c for c in candidates if c["cross_source"]]
    if cross:
        L.append("## 🔥 跨源热点(优先留意)\n")
        L.append(table(cross))
        L.append("")

    # 分类
    by_cat = {k: [] for k in CAT_ORDER}
    for c in candidates:
        by_cat.setdefault(c["category_guess"], by_cat["其他"]).append(c)
    for cat in CAT_ORDER:
        rows = by_cat.get(cat, [])
        if not rows:
            continue
        L.append(f"## {cat}({len(rows)})\n")
        L.append(table(rows))
        L.append("")

    L.append("---\n*生成于 "
             + datetime.now(CST).strftime("%Y-%m-%d %H:%M") + " · 浮世微言采集管道*\n")
    return "\n".join(L)


# ── 主流程 ───────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="浮世微言 · 过滤/去重/看板")
    ap.add_argument("--date", help="处理日期 YYYY-MM-DD(默认今天)")
    ap.add_argument("--candidates-dir", default=str(CANDIDATES_DIR))
    ap.add_argument("--filtered-dir", default=str(FILTERED_DIR))
    ap.add_argument("--board-dir", default=str(BOARD_DIR))
    ap.add_argument("--blacklist", default=str(BLACKLIST_PATH))
    ap.add_argument("--similarity", type=float, default=0.6,
                    help="跨源去重相似度阈值(0~1,越大越严格,默认 0.6)")
    args = ap.parse_args()

    date_str = args.date or datetime.now(CST).strftime("%Y-%m-%d")
    cand_path = Path(args.candidates_dir) / f"{date_str}.json"
    if not cand_path.exists():
        raise SystemExit(f"未找到候选清单 {cand_path}\n请先运行:python3 scripts/crawl.py --date {date_str}")

    raw_items = json.loads(cand_path.read_text(encoding="utf-8"))
    subs, regexes = load_blacklist(Path(args.blacklist))

    # ① 黑名单
    kept, block_hits = [], Counter()
    for it in raw_items:
        hit = hit_blacklist(it.get("title", ""), subs, regexes)
        if hit:
            block_hits[hit] += 1
        else:
            it["category_guess"] = refine_category(it)
            it["_norm"] = norm_title(it.get("title", ""))
            kept.append(it)

    # ② 跨源去重
    clusters = cluster(kept, args.similarity)
    candidates = [merge_cluster(c["members"]) for c in clusters]
    candidates.sort(key=lambda c: (-c["source_count"], -c["heat_max"]))

    stats = {
        "raw": len(raw_items),
        "blocked": sum(block_hits.values()),
        "block_top": "、".join(f"{k}×{v}" for k, v in block_hits.most_common(5)),
        "clusters": len(candidates),
        "cross": sum(1 for c in candidates if c["cross_source"]),
    }

    # 输出 filtered JSON(去掉内部字段)
    out_json = Path(args.filtered_dir) / f"{date_str}.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")

    # 输出看板
    out_md = Path(args.board_dir) / f"{date_str}.md"
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(render_board(date_str, candidates, stats), encoding="utf-8")

    # 摘要
    print(f"[filter] 候选 {stats['raw']} → 黑名单剔除 {stats['blocked']}"
          + (f"({stats['block_top']})" if stats["block_top"] else "")
          + f" → 去重后 {stats['clusters']} 话题(跨源 {stats['cross']})")
    print(f"[save] {out_json}")
    print(f"[save] {out_md}  ← 选题看板,供人工勾选")


if __name__ == "__main__":
    main()
