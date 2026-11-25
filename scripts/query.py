#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""acd-callgraph 只读查询 CLI（纯标准库，不联网、不写盘、不装依赖）。

图可以直接从发布 zip 里读（默认，不必解压），也可以指向解压后的 acd_graph.json。

    python scripts/query.py --callees av_make_error_string   # 它调用了谁
    python scripts/query.py --callers filter_frame           # 谁调用了它（同名会命中多个 id）
    python scripts/query.py --edge av_make_error_string av_strerror
    python scripts/query.py --selfcheck                      # 全图自检

名字匹配是**名字级**：NAME 命中裸名，也命中所有 NAME@... 的 id；
同名多定义（static 作用域）**不合并**，命中几个就报几个。
退出码：0 成功 / 1 无命中 / 2 参数或数据错误 / 3 自检不一致。
"""

import argparse
import io
import json
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

# 默认图路径锚在仓根（不是当前工作目录）：在任意目录调用本脚本都能找到 release/ 下的包。
DEFAULT_GRAPH = os.path.join(REPO_ROOT, "release", "acd-ffmpeg-n9.1-dev-b357bf8e.zip")
GRAPH_MEMBER = "acd_graph.json"

EXPECT_CALLERS = 38697     # caller 键数（实测）
EXPECT_EDGES = 114175      # 边总数（实测）

EXIT_OK = 0
EXIT_NO_HIT = 1
EXIT_USAGE = 2
EXIT_SELFCHECK = 3


class UsageError(Exception):
    """参数或数据问题：只打印一行，不抛栈，退出码 2。"""


def bare(name):
    """函数名部分：'f@ffmpeg-src#a#b.c' -> 'f'；裸名原样返回。"""
    return name.split("@", 1)[0]


def load_graph(path):
    """读图：.zip 用 zipfile 直接取成员；其他按 UTF-8 JSON 读。"""
    if not os.path.exists(path):
        raise UsageError("找不到图文件：%s（默认应放在 release/ 下，未解压也行）" % path)

    if path.lower().endswith(".zip"):
        try:
            zf = zipfile.ZipFile(path)
        except (zipfile.BadZipFile, OSError) as exc:
            raise UsageError("打不开 zip：%s（%s）" % (path, exc))
        with zf:
            members = [n for n in zf.namelist() if os.path.basename(n) == GRAPH_MEMBER]
            if not members:
                raise UsageError("zip 里没有 %s：%s" % (GRAPH_MEMBER, path))
            with zf.open(members[0]) as fh:
                return json.load(io.TextIOWrapper(fh, encoding="utf-8"))

    try:
        with io.open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError) as exc:
        raise UsageError("读不了图：%s（%s）" % (path, exc))


class Graph(object):
    """一张图的只读视图。索引全部懒建，单次查询只扫一遍。"""

    def __init__(self, db, path):
        self.path = path
        self.edges = db.get("edges") or {}
        self.summary = db.get("summary") or {}
        self._ids = None
        self._inbound = None

    def ids(self):
        """全图 id 全集：caller 键 ∪ callee 键（含裸名外部符号）。"""
        if self._ids is None:
            universe = set(self.edges)
            for node in self.edges.values():
                universe.update(((node or {}).get("calls") or {}).keys())
            self._ids = sorted(universe)
        return self._ids

    def match(self, name):
        """名字级匹配：完整 id 命中，或裸名等于 NAME。"""
        return [x for x in self.ids() if x == name or bare(x) == name]

    def calls_of(self, caller):
        return (self.edges.get(caller) or {}).get("calls") or {}

    def inbound(self):
        """callee id -> [(caller id, meta), ...]"""
        if self._inbound is None:
            idx = {}
            for caller, node in self.edges.items():
                for callee, meta in (((node or {}).get("calls") or {})).items():
                    idx.setdefault(callee, []).append((caller, meta or {}))
            self._inbound = idx
        return self._inbound

    def counts(self):
        callers = len(self.edges)
        edges = sum(len(((n or {}).get("calls") or {})) for n in self.edges.values())
        return callers, edges


def sources_of(meta):
    srcs = meta.get("sources")
    if srcs:
        return ",".join(str(x) for x in srcs)
    return str(meta.get("source") or "-")


def sites_of(meta, keep=3):
    sites = meta.get("call_sites") or []
    if not sites:
        return "-"
    txt = " ; ".join(str(s) for s in sites[:keep])
    if len(sites) > keep:
        txt += " (+%d)" % (len(sites) - keep)
    return txt


def trace_of(meta):
    tc = meta.get("trace_count")
    return 0 if tc is None else tc


def edge_line(peer, meta):
    return "  %-60s sources=%s  confidence=%s  call_sites=%s  trace_count=%s" % (
        peer, sources_of(meta), meta.get("confidence") or "-",
        sites_of(meta), trace_of(meta))


def edge_record(caller, callee, meta):
    return {
        "caller": caller,
        "callee": callee,
        "sources": meta.get("sources") or [],
        "confidence": meta.get("confidence"),
        "call_sites": meta.get("call_sites") or [],
        "trace_count": trace_of(meta),
    }


def dump_json(payload):
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def emit_id_list(name, ids, limit, as_json):
    """命中 id 列表：只截断打印，总数照报。"""
    if as_json:
        return
    print("命中 %d 个 id（名字级匹配，未合并）：%s" % (len(ids), name) if len(ids) > 1
          else "命中 1 个 id（名字级匹配）：%s" % ids[0])
    for i in ids[:limit]:
        print("  - %s" % i)
    if len(ids) > limit:
        print("  ...（其余 %d 个未列出，--limit 可调；总数 %d 不变）"
              % (len(ids) - limit, len(ids)))


def do_callees(graph, args):
    ids = graph.match(args.callees)
    payload = {
        "query": {"mode": "callees", "name": args.callees},
        "graph": graph.path,
        "matched_count": len(ids),
        "matched_ids": ids,
        "edges": [],
        "ok": True,
    }
    if not ids:
        payload["ok"] = False
        payload["error"] = "没有名字为 %r 的 id" % args.callees
        if args.as_json:
            dump_json(payload)
        else:
            print("无命中：图里没有名字为 %s 的函数（名字级匹配：NAME 或 NAME@...）"
                  % args.callees)
        return EXIT_NO_HIT

    emit_id_list(args.callees, ids, args.limit, args.as_json)

    for cid in ids[:args.limit]:
        calls = graph.calls_of(cid)
        rows = sorted(calls.items(), key=lambda kv: (-trace_of(kv[1] or {}), kv[0]))
        if not args.as_json:
            print("%s  ->  %d 条出边" % (cid, len(rows)))
        for callee, meta in rows[:args.limit]:
            meta = meta or {}
            payload["edges"].append(edge_record(cid, callee, meta))
            if not args.as_json:
                print(edge_line(callee, meta))
        if len(rows) > args.limit and not args.as_json:
            print("  ...（该 id 还有 %d 条出边未打印，--limit 可调）" % (len(rows) - args.limit))

    if len(ids) > args.limit and not args.as_json:
        print("...（其余 %d 个 id 的出边未打印，总数 %d）" % (len(ids) - args.limit, len(ids)))

    if args.as_json:
        dump_json(payload)
    return EXIT_OK


def do_callers(graph, args):
    ids = graph.match(args.callers)
    inbound = graph.inbound() if ids else {}
    payload = {
        "query": {"mode": "callers", "name": args.callers},
        "graph": graph.path,
        "matched_count": len(ids),
        "matched_ids": ids,
        "edges": [],
        "ok": True,
    }
    if not ids:
        payload["ok"] = False
        payload["error"] = "没有名字为 %r 的 id" % args.callers
        if args.as_json:
            dump_json(payload)
        else:
            print("无命中：图里没有名字为 %s 的函数（名字级匹配：NAME 或 NAME@...）"
                  % args.callers)
        return EXIT_NO_HIT

    emit_id_list(args.callers, ids, args.limit, args.as_json)

    total_edges = 0
    for tid in ids[:args.limit]:
        rows = sorted(inbound.get(tid, []), key=lambda kv: (-trace_of(kv[1] or {}), kv[0]))
        total_edges += len(rows)
        if not args.as_json:
            print("%s  <-  %d 个 caller" % (tid, len(rows)))
        if not rows and not args.as_json:
            print("  （无入边）")
        for caller, meta in rows[:args.limit]:
            meta = meta or {}
            payload["edges"].append(edge_record(caller, tid, meta))
            if not args.as_json:
                print(edge_line(caller, meta))
        if len(rows) > args.limit and not args.as_json:
            print("  ...（该 id 还有 %d 个 caller 未打印，--limit 可调）" % (len(rows) - args.limit))

    if len(ids) > args.limit and not args.as_json:
        print("...（其余 %d 个 id 的入边未打印，总数 %d）" % (len(ids) - args.limit, len(ids)))

    if total_edges == 0:
        payload["ok"] = False
        payload["error"] = "名字命中 %d 个 id，但图上都没有入边" % len(ids)
        if args.as_json:
            dump_json(payload)
        return EXIT_NO_HIT

    if args.as_json:
        dump_json(payload)
    return EXIT_OK


def do_edge(graph, args):
    cname, tname = args.edge
    caller_ids = [x for x in graph.match(cname) if x in graph.edges]
    callee_ids = graph.match(tname)

    payload = {
        "query": {"mode": "edge", "caller": cname, "callee": tname},
        "graph": graph.path,
        "caller_ids": caller_ids,
        "callee_ids": callee_ids,
        "edges": [],
        "ok": True,
    }

    found = []
    for cid in caller_ids:
        calls = graph.calls_of(cid)
        for tid in callee_ids:
            if tid in calls:
                found.append((cid, tid, calls[tid] or {}))

    if not found:
        payload["ok"] = False
        if not caller_ids:
            payload["error"] = "没有名字为 %r 的 caller" % cname
        elif not callee_ids:
            payload["error"] = "没有名字为 %r 的 callee" % tname
        else:
            payload["error"] = "图里没有这条边：%s -> %s" % (cname, tname)
        if args.as_json:
            dump_json(payload)
        else:
            print("无命中：%s" % payload["error"])
            if len(caller_ids) > 1 or len(callee_ids) > 1:
                print("（名字级候选：caller %d 个 / callee %d 个，逐对都比过了）"
                      % (len(caller_ids), len(callee_ids)))
        return EXIT_NO_HIT

    found.sort(key=lambda t: (-trace_of(t[2]), t[0], t[1]))
    if not args.as_json:
        print("命中 %d 条边（名字级匹配，未合并）：" % len(found))
    for cid, tid, meta in found:
        payload["edges"].append(edge_record(cid, tid, meta))
        if not args.as_json:
            print(edge_line(cid + " -> " + tid, meta))

    if args.as_json:
        dump_json(payload)
    return EXIT_OK


def do_selfcheck(graph, args):
    callers, edges = graph.counts()
    summary_total = graph.summary.get("total_edges")
    ok = (callers == EXPECT_CALLERS
          and edges == EXPECT_EDGES
          and (summary_total is None or summary_total == edges))

    payload = {
        "query": {"mode": "selfcheck"},
        "graph": graph.path,
        "callers": callers,
        "edges": edges,
        "expect_callers": EXPECT_CALLERS,
        "expect_edges": EXPECT_EDGES,
        "summary_total_edges": summary_total,
        "ok": ok,
    }

    if args.as_json:
        dump_json(payload)
        return EXIT_OK if ok else EXIT_SELFCHECK

    print("[selfcheck] %s" % graph.path)
    print("   caller 键数 = {:,}（期望 {:,}）".format(callers, EXPECT_CALLERS))
    print("   边总数     = {:,}（期望 {:,}）".format(edges, EXPECT_EDGES))
    print("   summary.total_edges = %s" % summary_total)
    print("   结论：%s" % ("PASS" if ok else "FAIL（图被改过或不是这张图）"))
    return EXIT_OK if ok else EXIT_SELFCHECK


def build_parser():
    parser = argparse.ArgumentParser(
        prog="query.py",
        description="acd-callgraph 只读查询（纯标准库；直接读 release/ 里的 zip，不必解压）",
        epilog="退出码：0 成功 / 1 无命中 / 2 参数或数据错误 / 3 自检不一致",
    )
    parser.add_argument("--graph", metavar="PATH", default=DEFAULT_GRAPH,
                        help="图来源：发布 zip（默认）或解压后的 acd_graph.json")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--callees", metavar="NAME", help="它调用了谁")
    group.add_argument("--callers", metavar="NAME", help="谁调用了它（同名会命中多个 id）")
    group.add_argument("--edge", nargs=2, metavar=("CALLER", "CALLEE"),
                       help="查一条边：CALLER CALLEE")
    group.add_argument("--selfcheck", action="store_true", help="枚举全图自检（38,697 / 114,175）")
    parser.add_argument("--limit", type=int, default=20, metavar="N",
                        help="最多打印多少个 id / 多少条边（默认 20；总数照样报）")
    parser.add_argument("--json", action="store_true", dest="as_json", help="输出机读 JSON")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.limit < 1:
        sys.stderr.write("错误：--limit 必须 >= 1（收到 %r）\n" % args.limit)
        return EXIT_USAGE

    try:
        graph = Graph(load_graph(args.graph), args.graph)
        if args.selfcheck:
            return do_selfcheck(graph, args)
        if args.callees is not None:
            return do_callees(graph, args)
        if args.callers is not None:
            return do_callers(graph, args)
        return do_edge(graph, args)
    except UsageError as exc:
        sys.stderr.write("错误：%s\n" % exc)
        return EXIT_USAGE
    except KeyboardInterrupt:
        sys.stderr.write("已中断\n")
        return EXIT_USAGE
    except Exception as exc:  # 兜底：不抛 Python 栈
        sys.stderr.write("错误：%s: %s\n" % (type(exc).__name__, exc))
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
