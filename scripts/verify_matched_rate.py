# -*- coding: utf-8 -*-
"""verify_matched_rate.py — 互证率（matched_rate）复算与判据

口径：docs/caliber.md §2.12（matched_rate）

    S = 静态族边 = sources 含 static 或 static-reg，且不含 asm
    R = 运行时边 = sources 含 runtime
    both = S 与 R 在 identity（file::func）粒度上的交集
    matched_rate = |both| / |R|

当前绑图（b357bf8e / 114,175 边）期望：
    |S| 92,892  |R| 45,187  both 28,782  rate 63.7%
    仅运行时 16,405   仅静态 64,110

可失败判据：
    1. both != 28,782          → 口径错（或图变了）
    2. 28,782 + 16,405 != 45,187 → 闭合错
    3. 28,782 + 64,110 != 92,892 → 闭合错
    4. 裸名粒度 join 必须得到不同值（68.4%）→ 若与 identity 相同，说明 join 没生效
"""
import argparse
import json
import sys

EXP = {
    "static": 92892,
    "runtime": 45187,
    "both": 28782,
    "only_runtime": 16405,
    "only_static": 64110,
    "rate_pct": 63.7,
    "bare_rate_pct": 68.4,
}

STATIC = {"static", "static-reg"}


def split_key(k):
    return tuple(k.split("@", 1)) if "@" in k else (k, None)


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def compute(g):
    edges = g["edges"]
    S, R = set(), set()
    S_bare, R_bare = set(), set()
    for caller, node in edges.items():
        if not isinstance(node, dict):
            continue
        ci = split_key(caller)
        cname = ci[0]
        for callee, m in (node.get("calls") or {}).items():
            if not isinstance(m, dict):
                continue
            src = set(m.get("sources") or [])
            cid = m.get("callee_id")
            if cid:
                kn, kf = split_key(cid)
                callee_i, callee_n = (kn, kf), kn
            else:
                callee_i, callee_n = (callee, None), callee
            if src & STATIC and "asm" not in src:
                S.add((ci, callee_i))
                S_bare.add(((cname, None), callee_n))
            if "runtime" in src:
                R.add((ci, callee_i))
                R_bare.add(((cname, None), callee_n))
    both = S & R
    both_bare = S_bare & R_bare
    return {
        "static": len(S),
        "runtime": len(R),
        "both": len(both),
        "only_runtime": len(R - S),
        "only_static": len(S - R),
        "rate_pct": round(100.0 * len(both) / len(R), 1) if R else 0.0,
        "bare_rate_pct": round(100.0 * len(both_bare) / len(R_bare), 1) if R_bare else 0.0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("graph", help="acd_graph.json 路径")
    ap.add_argument("--any", action="store_true", help="不比对期望值，只打印（换图时用）")
    a = ap.parse_args()

    got = compute(load(a.graph))
    print(json.dumps(got, ensure_ascii=False, indent=2))
    if a.any:
        return 0

    checks = [
        ("|both| = 28,782", got["both"] == EXP["both"]),
        ("|S| = 92,892", got["static"] == EXP["static"]),
        ("|R| = 45,187", got["runtime"] == EXP["runtime"]),
        ("闭合 R = both + only_runtime", got["both"] + got["only_runtime"] == got["runtime"]),
        ("闭合 S = both + only_static", got["both"] + got["only_static"] == got["static"]),
        ("rate = 63.7%", got["rate_pct"] == EXP["rate_pct"]),
        ("负例：裸名 join 必须不同（68.4%）", got["bare_rate_pct"] != got["rate_pct"]),
    ]
    fails = 0
    for name, ok in checks:
        print(("PASS  " if ok else "FAIL  ") + name)
        fails += 0 if ok else 1
    print("\n%d/%d PASS" % (len(checks) - fails, len(checks)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
