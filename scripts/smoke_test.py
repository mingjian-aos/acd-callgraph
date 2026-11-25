#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""query.py 的最小回归测试（纯标准库，不依赖 106 MB 全图，约 2 秒）。

覆盖：名字级同名不合并、callers、edge 命中/未命中、缺参数退出码 2、自检不一致退出码 3、
JSON 输出、缺图时的干净报错，以及 scripts/ 全部脚本可编译。

    python scripts/smoke_test.py     # 0 = 全 PASS，1 = 有 FAIL
"""

import json
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
QUERY = os.path.join(HERE, "query.py")

A1 = "alpha@ffmpeg-src#libx#a.c"
A2 = "alpha@ffmpeg-src#liby#a.c"
B = "beta@ffmpeg-src#libx#b.c"

# 造一张 3 节点的小图：alpha 有两个同名定义（A1 / A2），都调用 beta；beta 调裸名 gamma
FIXTURE = {
    "summary": {"total_edges": 3},
    "edges": {
        A1: {"calls": {B: {"source": "runtime-confirmed", "sources": ["runtime", "static"],
                          "confidence": "high", "call_sites": ["libx/a.c:10"],
                          "trace_count": 5}}},
        A2: {"calls": {B: {"source": "static", "sources": ["static"],
                          "confidence": "medium", "call_sites": ["liby/a.c:30"]}}},
        B: {"calls": {"gamma": {"source": "static", "sources": ["static"],
                               "confidence": "medium", "call_sites": ["libx/b.c:20"]}}},
    },
}

failures = []
CHECKS = [0]


def check(name, argv, want_code, want_out=None, want_err=None, forbid=None):
    CHECKS[0] += 1
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"  # 子进程统一按 UTF-8 输出，避免 Windows 代码页
    proc = subprocess.run([sys.executable, QUERY] + argv,
                          capture_output=True, env=env)
    out = proc.stdout.decode("utf-8", "replace")
    err = proc.stderr.decode("utf-8", "replace")

    problems = []
    if proc.returncode != want_code:
        problems.append("退出码 %d ≠ 期望 %d" % (proc.returncode, want_code))
    for s in (want_out or []):
        if s not in out:
            problems.append("stdout 缺 %r" % s)
    for s in (want_err or []):
        if s not in err:
            problems.append("stderr 缺 %r" % s)
    for s in (forbid or []):
        if s in out or s in err:
            problems.append("出现了不该有的 %r" % s)

    ok = not problems
    print("  %-26s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "  ← " + " / ".join(problems)))
    if not ok:
        failures.append(name)
    return out, err


def main():
    tmp = tempfile.mkdtemp(prefix="acd_smoke_")
    graph = os.path.join(tmp, "mini.json")
    with open(graph, "w", encoding="utf-8") as f:
        json.dump(FIXTURE, f, ensure_ascii=False)
    missing = os.path.join(tmp, "no_such_graph.zip")

    print("[fixture] %s" % graph)
    print("[case]")

    check("callees: 同名不合并", ["--graph", graph, "--callees", "alpha"], 0,
          want_out=["命中 2 个 id", "beta@ffmpeg-src#libx#b.c", "sources=runtime,static"],
          forbid=["Traceback"])
    check("callers: 反向命中", ["--graph", graph, "--callers", "beta"], 0,
          want_out=["alpha@ffmpeg-src", "2 个 caller"],
          forbid=["Traceback"])
    check("callers: 裸名 callee", ["--graph", graph, "--callers", "gamma"], 0,
          want_out=["beta@ffmpeg-src#libx#b.c"],
          forbid=["Traceback"])
    check("edge: 命中", ["--graph", graph, "--edge", "alpha", "beta"], 0,
          want_out=["sources=runtime,static"],
          forbid=["Traceback"])
    check("edge: 未命中 -> 1", ["--graph", graph, "--edge", "alpha", "nosuch_fn"], 1,
          want_out=["无命中"],
          forbid=["Traceback"])
    check("参数缺值 -> 2", ["--graph", graph, "--callees"], 2,
          want_err=["expected one argument"],
          forbid=["Traceback"])
    check("缺图 -> 2", ["--graph", missing, "--callees", "alpha"], 2,
          want_err=["找不到图"],
          forbid=["Traceback"])
    check("selfcheck 不一致 -> 3", ["--graph", graph, "--selfcheck"], 3,
          want_out=["FAIL", "3", "38,697"],
          forbid=["Traceback"])

    out, err = check("--json 可解析", ["--graph", graph, "--callees", "alpha", "--json"], 0,
                     forbid=["Traceback"])
    payload = None
    try:
        payload = json.loads(out)
    except Exception:
        pass
    CHECKS[0] += 1
    ok = isinstance(payload, dict) and payload.get("matched_count") == 2 \
        and len(payload.get("edges") or []) == 2
    print("  %-26s %s" % ("--json 结构（2 条边）", "PASS" if ok else "FAIL"))
    if not ok:
        failures.append("--json 结构")

    # 所有脚本可编译（语法层回归）
    CHECKS[0] += 1
    bad = []
    for fn in sorted(os.listdir(HERE)):
        if fn.endswith(".py"):
            try:
                py_compile.compile(os.path.join(HERE, fn), doraise=True)
            except py_compile.PyCompileError as exc:
                bad.append("%s: %s" % (fn, exc.msg.strip().splitlines()[-1]))
    print("  %-26s %s" % ("scripts/*.py 可编译", "PASS" if not bad else "FAIL: " + "; ".join(bad)))
    if bad:
        failures.append("py_compile")

    # 查看器双语：zh/en 键集相等、每个视图有英文标题、产物与模板同源
    CHECKS[0] += 1
    vp = []
    root = os.path.dirname(HERE)
    tpl_p = os.path.join(root, "viewer", "viewer-template.html")
    out_p = os.path.join(root, "viewer", "acd-viewer.html")
    js_p = os.path.join(root, "viewer", "acd-views.json")
    try:
        tpl = open(tpl_p, encoding="utf-8").read()
        block = tpl[tpl.index("const I18N"):tpl.index("let LANG=")]
        zh_part, en_part = block.split("en: {", 1)
        k_zh = set(re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*:'", zh_part))
        k_en = set(re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*:'", en_part))
        if k_zh != k_en:
            vp.append("zh/en 键集不等 %s" % sorted(k_zh ^ k_en)[:6])
        if len(k_zh) < 60:
            vp.append("双语键过少 (%d)" % len(k_zh))
        if "data-t=" not in tpl or "&lang=" not in tpl or "sliceBadge" not in tpl:
            vp.append("模板缺 data-t / lang 参数 / 切片徽标")
        html = open(out_p, encoding="utf-8").read()
        pre, suf = tpl.split("/*__DATA__*/", 1)
        if not (html.startswith(pre) and html.endswith(suf)):
            vp.append("产物与模板不同源（需重新 export_views.py）")
        views = json.load(open(js_p, encoding="utf-8"))["views"]
        for k, v in views.items():
            if not v.get("title_en") or not v.get("note_en"):
                vp.append("视图 %s 缺 title_en/note_en" % k)
    except Exception as exc:
        vp.append("%s: %s" % (type(exc).__name__, exc))
    print("  %-26s %s" % ("viewer 双语与同源", "PASS" if not vp else "FAIL  ← " + "; ".join(vp)))
    if vp:
        failures.append("viewer-i18n")

    # 双语方法文档：数字多重集必须与中文版逐项相同（“数字一个不动”的机器门禁）
    CHECKS[0] += 1
    dp = []

    def nums(rel):
        t = open(os.path.join(root, rel), encoding="utf-8").read()
        return Counter(x.rstrip(".,") for x in re.findall(r"\d[\d,\.]*", t))

    for zh, en in (("docs/caliber.md", "docs/caliber.en.md"),
                   ("docs/faq.md", "docs/faq.en.md")):
        try:
            a, b = nums(zh), nums(en)
            if a != b:
                dp.append("%s 数字不一致 +%s -%s"
                          % (en, sorted((b - a).items())[:4], sorted((a - b).items())[:4]))
        except Exception as exc:
            dp.append("%s: %s" % (en, exc))
    print("  %-26s %s" % ("docs 中英数字一致", "PASS" if not dp else "FAIL  ← " + "; ".join(dp)))
    if dp:
        failures.append("docs-i18n")

    shutil.rmtree(tmp, ignore_errors=True)
    print("\n汇总：%d 项，FAIL %d" % (CHECKS[0], len(failures)))
    if failures:
        print("FAIL: " + ", ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
