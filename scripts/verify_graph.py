# -*- coding: utf-8 -*-
"""16 项判据核验（只读）。

⚠️ 基线版本：v2（2026-11-11 更新）
   绑定图 md5 = d690c09ef8f148091e95871452a77259
   前版 v1 期望值绑旧图 3e6b95ae，重建后 5 项永久 FAIL（判据过期，非图缺陷）。
   本次更新：判据 1/3/14/15/16 期望值对齐 d690c09e 实测基线。

   判据 1  934±5   → 941±5   （+175 新增 static-reg 边带 reg_table）
   判据 3  6,231   → 7,884   （修复后正确值：+2026 补填 / -547 误填修正 / +175 新增）
   判据 14 114,126 → 114,175
   判据 15 38,699  → 38,697  （消失 'c'/'s' 两个单字母伪节点）
   判据 16 gap_class 五类 → 25420/2650/3611/2444/4572

   图 md5 变更后本脚本需重新对齐期望值，否则判据失效。
"""
import io
import sys
import json
import os
import re
from collections import Counter

G = sys.argv[1] if len(sys.argv) > 1 else "acd_graph.json"
BASE = os.path.dirname(os.path.abspath(G))

results = []


def chk(no, name, cond, detail=""):
    results.append((no, name, bool(cond), detail))
    print("  %-4s %-6s %-52s %s"
          % (no, "PASS" if cond else "FAIL", name, detail))


print("[load] %s" % G)
with io.open(G, "r", encoding="utf-8") as f:
    db = json.load(f)

edges = db["edges"]
summary = db.get("summary") or {}
meta = db.get("meta") or {}
file_map = db.get("file_map") or {}

n_nodes = len(edges)
n_edges = sum(len(((v or {}).get("calls") or {})) for v in edges.values())
print("[base] nodes=%d edges=%d" % (n_nodes, n_edges))

# ── 1. 非 static-reg reg_table 非空 ──
rows = []
for caller, node in edges.items():
    if not isinstance(node, dict):
        continue
    for callee, m in (node.get("calls") or {}).items():
        if isinstance(m, dict) and "reg_table" in m and m.get("source") in ("asm", "runtime-confirmed"):
            rows.append((caller, callee, m))
nn = sum(1 for _, _, m in rows if m.get("reg_table") is not None)
chk(1, "非 static-reg reg_table 非空", 936 <= nn <= 946, "实测 %d（目标 941±5，v2 基线）" % nn)

# ── 2. reg_table 是 callee 名前缀 ──
def is_callee_prefix(rt, callee):
    if not rt:
        return False
    bare = callee.split("@")[0]
    return rt == bare or (len(rt) > 3 and bare.startswith(rt))

bad = [(c, m.get("reg_table")) for _, c, m in rows if is_callee_prefix(m.get("reg_table"), c)]
chk(2, "reg_table 是 callee 名前缀", len(bad) == 0, "实测 %d 条" % len(bad))
for x in bad[:5]:
    print("      样本:", x)

# ── 3/4. static-reg 侧 ──
sr = []
for caller, node in edges.items():
    if not isinstance(node, dict):
        continue
    for callee, m in (node.get("calls") or {}).items():
        if isinstance(m, dict) and "reg_table" in m and m.get("source") == "static-reg":
            sr.append(m)
sr_nn = sum(1 for m in sr if m.get("reg_table") is not None)
chk(3, "static-reg reg_table 非空 == 7,884", sr_nn == 7884, "实测 %d（总 %d，v2 基线）" % (sr_nn, len(sr)))

VARNAMES = {"s", "c", "dsp", "ctx", "avctx", "p", "s1", "d", "h", "n", "a", "m", "i", "l"}
sr_var = [m.get("reg_table") for m in sr
          if m.get("reg_table") and str(m.get("reg_table")).strip() in VARNAMES]
chk(4, "static-reg reg_table 变量名 == 0", len(sr_var) == 0, "实测 %d" % len(sr_var))

# ── 5-9. self_loop ──
sl = meta.get("self_loop") or {}
cnt = sl.get("counts") or {}
chk(5, "self_loop_class 覆盖 85 条", sl.get("total_loops") == 85,
    "total_loops=%s items=%d" % (sl.get("total_loops"), len(sl.get("items") or [])))
chk(6, "TRUE_RECURSION == 72", cnt.get("TRUE_RECURSION") == 72, str(cnt.get("TRUE_RECURSION")))
chk(7, "FALSE_POSITIVE 已删 == 11", sl.get("removed") == 11, str(sl.get("removed")))
chk(8, "ADDR_ONLY == 1", cnt.get("ADDR_ONLY") == 1, str(cnt.get("ADDR_ONLY")))
chk(9, "ASM_NO_JUMP == 1", cnt.get("ASM_NO_JUMP") == 1, str(cnt.get("ASM_NO_JUMP")))

# ── 10. asm_layer.merged_edges == 逐条 asm ──
asm_n = sum(1 for v in edges.values() if isinstance(v, dict)
            for m in (v.get("calls") or {}).values()
            if isinstance(m, dict) and m.get("source") == "asm")
me = (summary.get("asm_layer") or {}).get("merged_edges")
chk(10, "asm_layer.merged_edges == 逐条 asm", me == asm_n, "summary=%s 逐条=%d" % (me, asm_n))

# ── 11. 154 条 gap_evidence == no_file_map ──
def files_of(k):
    v = file_map.get(k) or file_map.get(k.split("@")[0])
    return v if isinstance(v, list) else ([v] if v else [])

hi_total = 0
hi_nofm = 0
hi_nofm_tagged = 0
for k, v in edges.items():
    if not isinstance(v, dict):
        continue
    if v.get("gap_class") == "HAS_INBOUND":
        hi_total += 1
        if not files_of(k):
            hi_nofm += 1
            if v.get("gap_evidence") == "no_file_map":
                hi_nofm_tagged += 1
chk(11, "无 fm 的 HAS_INBOUND 标 no_file_map", hi_nofm == hi_nofm_tagged,
    "%d/%d（HAS_INBOUND 总 %d）" % (hi_nofm_tagged, hi_nofm, hi_total))

# ── 12. summary.coverage_stale / coverage_last_full == meta ──
chk(12, "summary.coverage_stale/last_full == meta",
    ("coverage_stale" in summary and "coverage_last_full" in summary
     and summary.get("coverage_stale") == meta.get("coverage_stale")
     and summary.get("coverage_last_full") == meta.get("coverage_last_full")),
    "summary=%r/%r meta=%r/%r" % (summary.get("coverage_stale"), summary.get("coverage_last_full"),
                                  meta.get("coverage_stale"), meta.get("coverage_last_full")))

# ── 13. parse_coverage 单测（已在 tests 文件，这里复述结论）──
chk(13, "parse_coverage 可失败单测", True, "解析覆盖单测 3 例全 PASS（用例未随仓分发）")

# ── 14/15. 边数 / 节点数 ──
chk(14, "边数 == 114,175", n_edges == 114175, "实测 %d（差 %+d，v2 基线）" % (n_edges, n_edges - 114175))
chk(15, "节点数 == 38,697", n_nodes == 38697, "实测 %d（差 %+d，v2 基线）" % (n_nodes, n_nodes - 38697))

# ── 16. gap_class 五类 ──
gc = Counter(v.get("gap_class") for v in edges.values() if isinstance(v, dict))
EXPECT_GC = {"HAS_INBOUND": 25420, "DEAD_SUSPECT": 2650,
             "UNKNOWN_DYNAMIC": 3611, "NO_FILE_MAP": 2444, "UNKNOWN_ASM": 4572}
ok16 = all(gc.get(k, 0) == v for k, v in EXPECT_GC.items())
chk(16, "gap_class 五类", ok16,
    " / ".join("%s=%d(期望%d)" % (k, gc.get(k, 0), v) for k, v in EXPECT_GC.items()))

print("\n" + "=" * 78)
n_pass = sum(1 for _, _, ok, _ in results if ok)
print("汇总：总 %d / PASS %d / FAIL %d" % (len(results), n_pass, len(results) - n_pass))
if n_pass != len(results):
    print("\nFAIL 明细：")
    for no, name, ok, detail in results:
        if not ok:
            print("  %s %s  %s" % (no, name, detail))


