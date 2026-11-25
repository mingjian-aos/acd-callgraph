#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从 ACD 全图导出瘦身视图，注入模板生成单文件查看器。

用法：
    python export_views.py --graph acd_graph.json

    默认写 viewer/viewer-template.html → viewer/acd-viewer.html + viewer/acd-views.json。
    想在别处另存一份、不覆盖默认产物时，显式指路径：
    python export_views.py --graph acd_graph.json \
        --out-html viewer/_scratch.html --out-json viewer/_scratch.json

只读图数据，不修改任何源文件。
"""
import json, re, os, sys, datetime, math, argparse
from collections import deque

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, "viewer", "viewer-template.html")
OUT_HTML = os.path.join(ROOT, "viewer", "acd-viewer.html")
OUT_JSON = os.path.join(ROOT, "viewer", "acd-views.json")

META_COMMIT = "818cecc6e1afab932cf4d40ef0d7b8cd40311a17"
META_CONFIGURE = "--prefix=G:/ffmpeg-install --disable-doc --disable-debug --enable-gpl"
KNOWN_LAYERS = ("static", "runtime", "asm", "static-reg")


def short_file(nid):
    if "@" not in nid:
        return nid
    loc = nid.split("@", 1)[1]
    parts = loc.split("#")
    if parts and parts[0].endswith("-src"):
        parts = parts[1:]
    return "/".join(parts)


def func_name(nid):
    return nid.split("@", 1)[0]


def layer_of(sources):
    src = [s for s in (sources or []) if s]
    if len(src) >= 2:
        return "multi"
    if src and src[0] in KNOWN_LAYERS:
        return src[0]
    return "static"


def build_view(graph, focus, depth, cap, title, note):
    edges = graph["edges"]
    rev = graph["_rev"]
    gap = graph["_gap"]
    focus = focus if focus in edges or focus in rev else None
    if focus is None:
        raise SystemExit("焦点节点不存在: %s" % focus)

    order, dist = [focus], {focus: 0}
    q = deque([focus])
    while q:
        u = q.popleft()
        if dist[u] >= depth:
            continue
        nbrs = list(edges.get(u, {}).get("calls", {}).keys()) + list(rev.get(u, ()))
        for v in nbrs:
            if v not in dist and len(dist) < cap:
                dist[v] = dist[u] + 1
                order.append(v)
                q.append(v)

    keep = set(order)
    deg = {}
    for u in keep:
        calls = edges.get(u, {}).get("calls", {})
        deg[u] = len([c for c in calls if c in keep]) + len([c for c in rev.get(u, ()) if c in keep])

    # ---- 同心环布局：焦点居中，按层外扩，同层按父节点聚簇，减少交叉 ----
    layers = {}
    for nid in order:
        layers.setdefault(dist[nid], []).append(nid)
    # 每个节点的父节点（上一层的邻居，取连接度最高者）
    parent = {}
    for d in sorted(layers):
        if d == 0:
            continue
        for v in layers[d]:
            cands = [u for u in list(edges.get(v, {}).get("calls", {}).keys()) + list(rev.get(v, ()))]
            cands = [u for u in cands if dist.get(u) == d - 1]
            parent[v] = max(cands, key=lambda u: deg.get(u, 0)) if cands else None
    pos = {focus: (0.0, 0.0)}
    prev_order = {focus: 0}
    for d in sorted(layers):
        if d == 0:
            continue
        row = layers[d]
        # 按父节点在上一层的顺序聚簇；无父的排到最后
        row.sort(key=lambda v: (prev_order.get(parent.get(v), 10 ** 6), -deg.get(v, 0), v))
        n = len(row)
        need = max(260.0, n * 20.0 / (2 * math.pi))
        R = need if d == 1 else max(need, max(math.hypot(*pos.get(parent.get(v), (0, 0))) for v in row) + 120.0)
        for i, v in enumerate(row):
            ang = 2 * math.pi * i / n - math.pi / 2
            pos[v] = (R * math.cos(ang), R * math.sin(ang))
        # 记录本层顺序，供下一层按父聚簇
        order_map = {v: i for i, v in enumerate(row)}
        prev_order = {v: order_map.get(v, i) for i, v in enumerate(row)}

    nodes = []
    for nid in order:
        nodes.append({
            "i": nid,
            "n": func_name(nid),
            "f": short_file(nid),
            "g": gap.get(nid, "HAS_INBOUND"),
            "L": dist[nid],
            "x": round(pos[nid][0], 1),
            "y": round(pos[nid][1], 1),
            "deg": deg.get(nid, 0),
        })

    links = []
    for u in keep:
        for callee, pay in edges.get(u, {}).get("calls", {}).items():
            if callee not in keep:
                continue
            ev = (pay.get("evidence") or {}).get("runtime") or {}
            sites = pay.get("call_sites") or []
            links.append([
                u, callee, layer_of(pay.get("sources")),
                len(pay.get("sources") or []),
                sites[0] if sites else "",
                ev.get("trace_count") or 0,
                sorted({s for s in (pay.get("sources") or []) if s}),  # 逐层出处，供证据页四格
            ])

    return {
        "title": title,
        "note": note,
        "focus": focus,
        "depth": depth,
        "nodes": nodes,
        "links": links,
        "stats": {
            "nodes": len(nodes),
            "links": len(links),
            "by_layer": {k: sum(1 for l in links if l[2] == k) for k in ("static", "runtime", "asm", "static-reg", "multi")},
            "by_gap": {k: sum(1 for n in nodes if n["g"] == k) for k in ("HAS_INBOUND", "UNKNOWN_ASM", "UNKNOWN_DYNAMIC", "DEAD_SUSPECT", "NO_FILE_MAP")},
        },
    }


def pick(edges, want):
    """按函数名挑焦点；找不到就退化为子串匹配，再不行取出度最高的节点。"""
    exact = [k for k in edges if func_name(k) == want]
    if exact:
        return exact[0]
    loose = [k for k in edges if want and want in func_name(k)]
    if loose:
        return loose[0]
    return max(edges, key=lambda k: len(edges[k].get("calls", {})))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graph", default="acd_graph.json", help="全图 JSON 路径（默认 acd_graph.json）")
    # 可指定模板与产物路径，缺省与旧版一致
    ap.add_argument("--template", default=None, help="模板 HTML（默认 viewer/viewer-template.html）")
    ap.add_argument("--out-html", default=None, help="产物 HTML（默认 viewer/acd-viewer.html）")
    ap.add_argument("--out-json", default=None, help="瘦身数据 JSON（默认 viewer/acd-views.json）")
    args = ap.parse_args()

    tpl_path = args.template or TPL
    out_html = args.out_html or OUT_HTML
    out_json = args.out_json or OUT_JSON

    print("读取图:", args.graph)
    with open(args.graph, "r", encoding="utf-8") as f:
        raw = json.load(f)

    edges = raw["edges"]
    rev = {}
    gap = {}
    total_links = 0
    for caller, node in edges.items():
        gap[caller] = node.get("gap_class", "HAS_INBOUND")
        for callee in node.get("calls", {}):
            rev.setdefault(callee, set()).add(caller)
            total_links += 1
    rev = {k: tuple(v) for k, v in rev.items()}

    graph = {"edges": edges, "_rev": rev, "_gap": gap}
    print("节点(caller) %d ｜ 边 %d ｜ 反向索引 %d" % (len(edges), total_links, len(rev)))

    # 汇编层关联度最高的节点（asm 边最多）
    asm_deg = {}
    for caller, node in edges.items():
        for callee, pay in node.get("calls", {}).items():
            if "asm" in (pay.get("sources") or []):
                asm_deg[caller] = asm_deg.get(caller, 0) + 1
                asm_deg[callee] = asm_deg.get(callee, 0) + 1
    asm_hub = max(asm_deg, key=lambda k: asm_deg[k]) if asm_deg else None

    specs = [
        ("decode", "decode_simple_internal", 2, 160, "① 解码主路径", "运行时边如何补上静态看不到的调用",
         "① Decode main path", "How runtime edges fill in calls static parsing cannot see"),
        ("asm", "ff_hevc_dsp_init_x86", 2, 160, "② 汇编交叉点", "一个 C 分发函数指向 238 个汇编实现",
         "② Assembly crosspoint", "One C dispatch function pointing at 238 assembly implementations"),
        ("gray", None, 3, 300, "③ 未触达盲区", "主动画出自己没做到的部分",
         "③ Unreached blind spot", "Deliberately drawing the part we did not reach"),
    ]

    views = {}
    for key, want, depth, cap, title, note, title_en, note_en in specs:
        if key == "gray":
            # 挑一个总连接度最大的 DEAD_SUSPECT 节点做焦点
            cand = sorted(
                (k for k, v in gap.items() if v == "DEAD_SUSPECT"),
                key=lambda k: -(len(edges[k].get("calls", {})) + len(rev.get(k, ()))),
            )
            focus = cand[0] if cand else pick(edges, "decode_simple_internal")
        elif want:
            focus = pick(edges, want)
        v = build_view(graph, focus, depth, cap, title, note)
        v["title_en"] = title_en
        v["note_en"] = note_en
        views[key] = v
        s = v["stats"]
        print("  %-7s 焦点=%-32s 节点%4d 边%5d  %s" % (key, func_name(focus)[:32], s["nodes"], s["links"], s["by_layer"]))

    payload = {
        "meta": {
            "anchor": "b357bf8ea8a4b6bae4892ab99254bf2a",
            "commit": META_COMMIT,
            "configure": META_CONFIGURE,
            "total_nodes": len(edges),
            "total_edges": total_links,
            "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "source": os.path.basename(args.graph),
        },
        "views": views,
    }

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    with open(tpl_path, "r", encoding="utf-8") as f:
        tpl = f.read()
    inline = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    html = tpl.replace("/*__DATA__*/", inline)
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)

    print("已写出:")
    for p in (out_json, out_html):
        print("   %s  %.2f MB" % (p, os.path.getsize(p) / 1048576))


if __name__ == "__main__":
    main()



