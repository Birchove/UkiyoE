#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
roll-by.py —— 为「站主整理」的条目,从笔名池中以 *真随机* 抽取一枚署名,
写入该条目 frontmatter 的 `by` 字段。

用法:
  python3 scripts/roll-by.py src/content/entries/某篇.md [...]   # 缺 by 者补署名
  python3 scripts/roll-by.py src/content/entries/*.md            # 批量补缺
  python3 scripts/roll-by.py --reroll <files>                    # 已署名也重新抽取

说明:
  - 笔名池在 config/pen-names.json —— 增删笔名只改这一处。
  - 随机源为 secrets.choice,底层 os.urandom,即密码学真随机;
    既非伪随机种子,也不按文件名固定,故每次抽取独立、不可预测。
  - 署名在「执笔时」抽取一次并落盘,之后 *稳定*:构建(build)只读取渲染,
    绝不再改动 by。重复运行本脚本对已署名条目默认跳过(幂等),除非 --reroll。
  - 贡献稿(非站主整理)请留空 by,站点即不显示署名。
"""
import json
import re
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POOL_PATH = ROOT / "config" / "pen-names.json"


def load_pool():
    names = [str(n).strip() for n in json.loads(POOL_PATH.read_text(encoding="utf-8"))]
    names = [n for n in names if n]
    if not names:
        sys.exit("[error] 笔名池为空:config/pen-names.json")
    return names


def assign(text, pool, reroll):
    """返回 (新文本, 抽中的笔名或None, 说明)。"""
    if not text.startswith("---"):
        return text, None, "无 frontmatter,跳过"
    nl = text.find("\n", 3)                 # 首行 '---' 之后的换行
    end = text.find("\n---", nl)            # frontmatter 结束的 '\n---'
    if end == -1:
        return text, None, "frontmatter 未闭合,跳过"
    inner = text[nl + 1:end]               # 不含两侧 --- 的正文
    tail = text[end:]                       # 以 '\n---' 开头,含正文体
    lines = inner.split("\n")

    bi = next((i for i, ln in enumerate(lines) if re.match(r"^by\s*:", ln)), None)
    if bi is not None and not reroll:
        m = re.match(r'^by\s*:\s*["\']?(.*?)["\']?\s*$', lines[bi])
        return text, (m.group(1) if m else ""), "已署名,跳过(用 --reroll 重抽)"

    name = secrets.choice(pool)            # 真随机
    new_line = f'by: "{name}"'
    if bi is not None:
        lines[bi] = new_line
    else:
        ti = next((i for i, ln in enumerate(lines) if re.match(r"^title\s*:", ln)), None)
        if ti is not None:
            lines.insert(ti + 1, new_line)  # 紧跟标题,署名靠前
        else:
            lines.append(new_line)
    new_inner = "\n".join(lines)
    return text[: nl + 1] + new_inner + tail, name, "重抽" if bi is not None else "新署名"


def main():
    args = sys.argv[1:]
    reroll = "--reroll" in args
    files = [a for a in args if a != "--reroll"]
    if not files:
        sys.exit(__doc__)
    pool = load_pool()
    for f in files:
        p = Path(f)
        if not p.exists():
            print(f"[skip] 不存在: {f}")
            continue
        text = p.read_text(encoding="utf-8")
        new_text, name, msg = assign(text, pool, reroll)
        if new_text != text:
            p.write_text(new_text, encoding="utf-8")
        print(f'  {p.name:<24} → {name or "(无)":<8} [{msg}]')


if __name__ == "__main__":
    main()
