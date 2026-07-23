#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
crawl.py —— 浮世微言 · 热搜采集脚本(① 采集)

职责:从自部署的 DailyHotApi 拉取各平台热榜 → 归一化为统一字段 →
      按日落盘到 data/candidates/YYYY-MM-DD.json(史料底稿,全量快照)。

设计要点:
  - 纯标准库,无需 pip 安装任何依赖;
  - 单源失败不影响整体(隔离 + 退避重试 + 日志);
  - 同日多次运行会自动**合并去重**(按 来源+标题),不覆盖当天已有快照;
  - `--mock` 可离线生成样例数据,用于在未部署 Docker 时跑通整条管道(filter.py)。

用法:
  python3 scripts/crawl.py                 # 正常采集(需 DailyHotApi 已运行)
  python3 scripts/crawl.py --mock          # 离线生成样例数据(测试用)
  DAILYHOT_API=http://192.168.1.10:6688 python3 scripts/crawl.py   # 指定实例

数据源在 config/sources.json 配置;DailyHotApi 部署见 docs/dailyhot-docker.md。
本脚本只做「采集 + 存档」;过滤/打标/去重/看板由 filter.py 完成。
"""

import argparse
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# ── 路径 ─────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "sources.json"
DATA_DIR = REPO_ROOT / "data" / "candidates"

# 北京时间(热搜口径以国内时间为准)
CST = timezone(timedelta(hours=8))

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36 DailyHotCrawler/1.0"
)


# ── 工具函数 ─────────────────────────────────────────────────
def now_cst():
    return datetime.now(CST)


def to_int(value):
    """把各源五花八门的热度值(整数/字符串/'1.2万'/'3亿'/空)归一为 int。"""
    if value in (None, ""):
        return 0
    s = str(value).replace(",", "").strip()
    if not s:
        return 0
    mult = 1
    if s.endswith("万"):
        mult, s = 10_000, s[:-1]
    elif s.endswith("亿"):
        mult, s = 100_000_000, s[:-1]
    try:
        return int(float(s) * mult)
    except ValueError:
        return 0


def norm_title(title):
    """归一化标题,用于去重:全角转半角、去空白与常见话题符号、转小写。"""
    s = unicodedata.normalize("NFKC", title or "")
    s = re.sub(r"[#\s　]+", "", s)               # 去掉 # 话题符号与空白
    s = re.sub(r"[,。.!?,.!?、:;:;;'\"“”‘’()()]", "", s)
    return s.lower()


def load_config(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── 网络采集 ─────────────────────────────────────────────────
def fetch_source(base_url, route, timeout=15, retries=3):
    """抓取单个源,返回 (items_list, error_str)。失败返回 ([], 错误信息)。"""
    url = f"{base_url.rstrip('/')}/{route}"
    last_err = ""
    for attempt in range(1, retries + 1):
        try:
            req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            items = payload.get("data")
            if not isinstance(items, list):
                return [], f"返回结构异常(无 data 数组): {url}"
            return items, ""
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as e:
            last_err = f"{type(e).__name__}: {e}"
            if attempt < retries:
                time.sleep(1.5 * attempt)   # 退避重试
    return [], last_err


def normalize(meta, raw, idx, fetched_at):
    """把一条原始热榜项归一化为统一字段。"""
    if not isinstance(raw, dict):
        raw = {"title": str(raw)}
    title = (raw.get("title") or raw.get("name") or "").strip()
    if not title:
        return None
    url = raw.get("url") or raw.get("mobileUrl") or raw.get("link") or ""
    return {
        "source": meta["key"],
        "source_label": meta["label"],
        "title": title,
        "url": url,
        "heat": to_int(raw.get("hot", raw.get("heat", 0))),
        "rank": to_int(raw.get("index", raw.get("rank", 0))) or idx,
        "fetched_at": fetched_at,
        "category_guess": meta["category_guess"],
        "tags": [],
        "desc": (raw.get("desc") or raw.get("description") or "").strip(),
        "type": (raw.get("type") or "").strip(),
    }


# ── 离线样例(--mock) ────────────────────────────────────────
def mock_sources():
    """生成带‘跨源重复 / 应被黑名单命中’的样例,供测试整条管道。

    覆盖三种情形:
      ① 近同题登上多平台(应被 filter 合并为一个跨源候选);
      ② 应被黑名单剔除(花边 / 政治 / 无意义);
      ③ 正常候选,分散于各分类。
    """
    ts = now_cst().isoformat(timespec="seconds")

    def mk(source, label, cat, rows):
        out = []
        for i, (title, heat, url) in enumerate(rows, 1):
            out.append({
                "source": source, "source_label": label, "title": title,
                "url": url, "heat": heat, "rank": i, "fetched_at": ts,
                "category_guess": cat, "tags": [], "desc": "", "type": "",
            })
        return out

    items = []
    # ① 跨源近同题:同一事件登上 weibo / baidu / toutiao(应合并为一个跨源候选)
    items += mk("weibo", "微博热搜", "时事", [
        ("多所高校宣布取消期末统考", 4120000, "https://s.weibo.com/weibo?q=期末统考"),
        ("某顶流男星被曝隐婚生子", 5480000, "https://s.weibo.com/weibo?q=顶流"),   # 花边→应剔除
        ("外交部回应某国际议题", 2100000, "https://s.weibo.com/weibo?q=外交"),       # 政治→应剔除
    ])
    items += mk("baidu", "百度热搜", "时事", [
        ("多所高校宣布取消期末统考", 1760000, "https://www.baidu.com/s?wd=期末统考"),
        ("国务院发布某项政策文件", 1500000, "https://www.baidu.com/s?wd=国务院"),   # 政治→应剔除
    ])
    items += mk("toutiao", "今日头条", "时事", [
        ("多所高校宣布取消期末统考引热议", 980000, "https://toutiao.com/期末统考"),
    ])
    # ② / ③ 其余正常与应剔除样例
    items += mk("zhihu", "知乎热榜", "时事", [
        ("如何看待年轻人「断亲」,不愿走亲戚?", 1280000, "https://www.zhihu.com/question/断亲"),
        ("为什么现在的年味越来越淡了", 640000, "https://www.zhihu.com/question/年味"),
    ])
    items += mk("bilibili", "哔哩哔哩", "风物", [
        ("【科普】古人怎么过夏天", 420000, "https://b23.tv/夏天"),
        ("全网爆火的谐音梗合集,笑不活了", 880000, "https://b23.tv/谐音梗"),  # 笑语候选(应保留,勿误杀)
    ])
    items += mk("douyin", "抖音热点", "时事", [
        ("年轻人断亲不走亲戚", 2600000, "https://www.douyin.com/hot/断亲"),
        ("太帅了 某网红走红", 500000, "https://www.douyin.com/hot/网红"),           # 无意义(留待人工判断)
    ])
    return items


# ── 落盘(合并去重) ─────────────────────────────────────────
def merge_and_save(items, out_path):
    """读入当天已有快照,按 (来源, 归一标题) 合并去重,保留最新 fetched_at。"""
    existing = []
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = []

    pool = {}
    for it in existing + items:
        key = (it.get("source"), norm_title(it.get("title")))
        cur = pool.get(key)
        if cur is None or (it.get("fetched_at", "") >= cur.get("fetched_at", "")):
            pool[key] = it
    merged = sorted(pool.values(), key=lambda x: (x["source"], x["rank"]))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, out_path)
    return len(merged)


# ── 主流程 ───────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="浮世微言 · 热搜采集")
    ap.add_argument("--mock", action="store_true", help="离线生成样例数据(测试用)")
    ap.add_argument("--date", help="指定存档日期 YYYY-MM-DD(默认今天)")
    ap.add_argument("--config", default=str(CONFIG_PATH), help="数据源配置路径")
    ap.add_argument("--data-dir", default=str(DATA_DIR), help="候选清单输出目录")
    ap.add_argument("--base-url", help="覆盖 DailyHotApi 地址(默认读环境变量或配置)")
    ap.add_argument("--timeout", type=int, default=15, help="单源超时秒数")
    ap.add_argument("--retries", type=int, default=3, help="单源重试次数")
    args = ap.parse_args()

    cfg = load_config(args.config)
    date_str = args.date or now_cst().strftime("%Y-%m-%d")
    out_path = Path(args.data_dir) / f"{date_str}.json"

    if args.mock:
        items = mock_sources()
        print(f"[mock] 生成样例 {len(items)} 条")
    else:
        base_url = (
            args.base_url
            or os.environ.get(cfg.get("base_url_env", "DAILYHOT_API"))
            or cfg.get("base_url_default", "http://localhost:6688")
        )
        print(f"[crawl] DailyHotApi @ {base_url}")
        items, ok, fail = [], 0, 0
        for meta in cfg["sources"]:
            if not meta.get("enabled", True):
                print(f"  - 跳过(已停用): {meta['label']}")
                continue
            raw, err = fetch_source(base_url, meta["route"], args.timeout, args.retries)
            if err:
                fail += 1
                print(f"  ✗ {meta['label']:<8} 失败: {err}")
                continue
            fetched_at = now_cst().isoformat(timespec="seconds")
            got = 0
            for idx, r in enumerate(raw, 1):
                it = normalize(meta, r, idx, fetched_at)
                if it:
                    items.append(it)
                    got += 1
            ok += 1
            print(f"  ✓ {meta['label']:<8} {got} 条")
        print(f"[crawl] 完成:成功 {ok} 源 / 失败 {fail} 源 / 共 {len(items)} 条")
        if not items:
            print("没有采集到任何数据(检查 DailyHotApi 是否已启动)。", file=sys.stderr)
            sys.exit(1)

    total = merge_and_save(items, out_path)
    print(f"[save] 已写入 {out_path}(当日候选池共 {total} 条)")
    print(f"\n下一步: python3 scripts/filter.py --date {date_str}")


if __name__ == "__main__":
    main()
