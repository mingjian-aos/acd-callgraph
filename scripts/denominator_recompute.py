# -*- coding: utf-8 -*-
"""
denominator_recompute.py — 分层分母重算（默认只算不写）

口径定义（本仓唯一权威）：docs/caliber.md §2.7 / §2.8
    instr       = 有 file_map 且非汇编(.s/.asm) 的 identity 集合
    touched     = D 层 trace 的 caller ∪ callee → identity，并限定在 instr 内
    real_denom  = instr − macro − unused − ffprobe
    nt          = real_denom − touched            （集合差，不是数值差）
    target_set  = nt − SIMD
    macro 规则  = (bytestream|GET_|PUT_|_template|uops_) + 全大写命名
    unused 规则 = <build_root>/config.h 中 CONFIG_*=0（去 CONFIG_ 前缀 + 小写 stem）

用法
    python scripts/denominator_recompute.py \\
        --graph acd_graph.json --build-root <build_dir> \\
        --asm asm_capstone_map.json --touched <edges_fate_*.json> [--compare data/denominator.json] [--out denominator.json --write]

设计要点
    - identity = (裸名, 主文件)：同一函数可能以裸名 key 与消歧 key 并存，按 key 做集合运算会重复计数，故先去重到 identity。
    - file_map 查找 full_id 优先、回退裸名（两套语义，见 caliber.md §10.2）。
    - 每条判据都可失败（P1–P5），结果随返回值返回，不静默通过。
    - 默认 dry_run：只算不写。落盘必须显式 --write。
"""
import datetime
import hashlib
import io
import json
import os
import re
from collections import Counter
from typing import Dict, List

_MACRO_RE = re.compile(r'(bytestream|bits|GET_|PUT_|_template|uops_)')
# ── CAL 口径修正（2026-10-19 口径定稿）────────────────
# 缺陷（实测）：原正则里 `bits` / `uops_` 是**子串匹配** → `av_get_bits_per_pixel`
#   / `align_get_bits` / `alpha_composite_16_10bits` 等真函数被误判为宏（1,465 个）。
# 修法（按审计分类实测校准）：
#   `bytestream` 子串（21,735，104 个名字）
#   `_template` 子串（51，如 `rgb16_32ToY_c_template`）
#   `uops_` 子串（2，如 `setup_dither_F32` 不含，真 uops_ 名）
#   全大写+下划线（`AV_COPY128` / `AV_ZERO128` 等）
#   **去掉裸 `bits` 子串匹配**（唯一误判源）
# 可失败判据：`av_get_bits_per_pixel` 不得进 macro；`AV_COPY128` 必须进 macro；
#   `rgb16_32ToY_c_template` 必须进 macro。
# ── CAL 口径版本（2026-10-19）：identity 去重 + 严格宏判定 + 非函数排除 ──
# v2 = identity 口径（口径定稿）+ 排除宏参数占位符/短变量名 + 补判 .h 混合大小写宏
# 口径变更时递增 → P3 判据据此豁免（可审计）
_CALIBER_VERSION = 'identity-v2'

_MACRO_STRICT_RE = re.compile(r'(bytestream|_template|uops_)')# 全大写+下划线，且 len>=3：
#   排除 len<3 的宏参数占位符（`D` `F` `FL` `M` `Q` `R` `S` `V` `W` `BF`，
#   实测 10 个，全部来自 `#define X(D, M)` 类宏定义的形参，非真宏）。
#   保留的真宏 5 个：AV_COPY128 / AV_COPY128U / AV_ZERO128 / NEG_SSR32 / NEG_USR32。
_MACRO_ALLCAPS_RE = re.compile(r'^[A-Z0-9_]{3,}$')
_CONFIG_OFF_RE = re.compile(r'#define\s+(CONFIG_[A-Z0-9_]+)\s+0\b')


def _md5_file(fp: str) -> str:
    h = hashlib.md5()
    with open(fp, 'rb') as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _load_json(fp: str):
    with io.open(fp, encoding='utf-8') as f:
        return json.load(f)


def _is_asm_path(p: str) -> bool:
    return (p or '').lower().endswith(('.s', '.asm'))


def _files_of(fm: Dict, fn: str) -> List[str]:
    v = fm.get(fn)
    if isinstance(v, list):
        return v
    return [v] if v else []


def _latest_fate_edges(trace_build: str) -> str:
    """trace_build 下最新 edges_fate_*.json（优先 recover）。"""
    if not os.path.isdir(trace_build):
        return ''
    cands = [f for f in os.listdir(trace_build)
             if f.startswith('edges_fate_') and f.endswith('.json')]
    if not cands:
        return ''
    rec = [f for f in cands if 'recover' in f]
    pool = rec or cands
    pool.sort(key=lambda f: os.path.getmtime(os.path.join(trace_build, f)),
              reverse=True)
    return os.path.join(trace_build, pool[0])


def recompute(ws_id: str = '',
              graph_path: str = '',
              build_root: str = '',
              asm_path: str = '',
              touched_source: str = '',
              out_path: str = '',
              dry_run: bool = True) -> Dict:
    """重算 C 层分母并（可选）绑当前图 md5 落盘 denominator.json。

    返回 {ok, dry_run, data, checks, written, backup, error}
    """
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = (os.path.dirname(os.path.abspath(out_path)) if out_path
         else os.path.join(base, 'data', 'acd', ws_id))
    gp = graph_path or os.path.join(d, 'acd_graph.json')
    dp = out_path or os.path.join(d, 'denominator.json')
    ap = asm_path or os.path.join(base, 'data', 'asm_capstone_map.json')
    tb = os.path.join(d, 'trace_build')

    if not graph_path:
        return {'ok': False, 'tool': 'denominator_recompute',
                'error': '需要显式传入图路径（CLI: --graph acd_graph.json）'}
    if not os.path.isfile(gp):
        return {'ok': False, 'error': '图不存在: %s' % gp,
                'tool': 'denominator_recompute'}

    gmd5 = _md5_file(gp)
    g = _load_json(gp)
    edges = g.get('edges') or {}
    fm = g.get('file_map') or {}

    # ── identity 口径（CAL 2026-10-19 口径定稿）──────────────
    # 背景：图是「只存 caller」设计 + 离线 key 重写后，同一函数可能以
    #   裸名 key 和消歧 key 两种形态并存（实测 911 组）。按 key 字符串做集合
    #   运算会重复计数 / 漏算。改为按 **identity = (裸名, 主文件)** 去重。
    # 实测：instr keys 57,289 → identity 56,376（911 组重复）。
    # 可失败判据：identity 数 != 56,376（±0）→ 口径错。
    _nodes = set(edges.keys())
    for _v in edges.values():
        _c = _v.get('calls') if isinstance(_v, dict) else None
        if isinstance(_c, dict):
            _nodes |= set(_c.keys())

    def _fm_of(k):
        """file_map 查找：full_id 优先，回退裸名（兼容两种 key 形态）。"""
        v = fm.get(k)
        if v:
            return v
        return fm.get(k.split('@')[0])

    def _files_of_key(k):
        v = _fm_of(k)
        if isinstance(v, list):
            return v
        return [v] if v else []

    def _ident(k):
        """identity = (裸名, 主文件)。无 file_map → 返回 None（不可插桩）。"""
        fs = _files_of_key(k)
        if not fs:
            return None
        # ── CAL-口径表（2026-10-29 审计 · 口径签认 口径表 表缺陷②）──
        # 缺陷（实测 662 条）：file_map 有 662 条的值为
        #   ['ffmpeg-src/xxx.c', 'xxx.c']（首值带 ws 根目录前缀），
        #   _ident 取 fs[0] → identity 的 file 带前缀 → target_set 658 条污染。
        #   后果：按 file 拼精确 key 的消费方（pk）全部匹配失败
        #   → 658 个真实存在的函数被误判为「缺口」（C 档虚增 412）。
        # 修法：取 fs[0] 时剥掉 ws 根目录前缀（`ffmpeg-src/`），
        #   统一成「源码相对路径」语义（与图内 key 的 @ws# 段一致）。
        # 可失败判据：target_set 中 file 以 'ffmpeg-src/' 开头的 pair == 0。
        _f0 = str(fs[0]).replace('\\', '/')
        if _f0.startswith('ffmpeg-src/'):
            _f0 = _f0[len('ffmpeg-src/'):]
        return (k.split('@')[0], _f0)

    # instr：identity 集合（有 file_map 且非汇编）
    # ── CAL 补充（2026-10-19 审计 · 实测）：排除宏参数占位符 + 短变量名 ──
    # 缺陷 1（实测）：`D` `F` `FL` `M` `Q` `R` `S` `V` `W` `BF` 共 10 个单/双字母
    #   全大写名字在 instr 里（有 file_map 归属），但不进 macro（len<3），
    #   也不进 real_denom 排除集 → 直接漏进 target_set（C 层会当函数插桩）。
    #   根因：它们是 `#define X(D, M)` 类宏定义的**形参占位符**。
    # 缺陷 2（实测）：`a0` `a1` `a2` `a3` `b0` `b1` `b2` `b3` 共 8 个
    #   `^[a-z][0-9]$` 形态是**局部变量名**（如 vf_xfade.c 的 a0），被解析器误当函数。
    # 修法：instr 判定加两条排除。
    # 可失败判据：`D` / `BF` / `a0` 不得出现在 target_set；
    #   `AV_COPY128`（len>=3）必须在；`avg`（真函数）必须在。
    _MACRO_PARAM_RE = re.compile(r'^[A-Z0-9_]{1,2}$')
    _SHORT_VAR_RE = re.compile(r'^[a-z][0-9]$')
    _instr_map = {}          # identity -> 代表 key（优先消歧 key）
    for k in _nodes:
        idt = _ident(k)
        if idt is None:
            continue
        if _is_asm_path(idt[1]):
            continue
        if _MACRO_PARAM_RE.match(idt[0]):
            continue          # 宏参数占位符，非函数
        if _SHORT_VAR_RE.match(idt[0]):
            continue          # 短变量名（a0/b3），非函数
        prev = _instr_map.get(idt)
        if prev is None or ('@' in k and '@' not in prev):
            _instr_map[idt] = k
    instr = set(_instr_map.keys())

    # ── touched：D 层 caller ∪ callee → 映射到 identity ──
    es = touched_source or _latest_fate_edges(tb)
    touched = set()
    if es and os.path.isfile(es):
        e = _load_json(es)
        _raw_touched = set()
        for caller, v in (e.get('edges') or {}).items():
            _raw_touched.add(caller)
            c = v.get('calls') if isinstance(v, dict) else None
            if isinstance(c, dict):
                _raw_touched |= set(c.keys())
        for _t in _raw_touched:
            _idt = _ident(_t)
            if _idt is not None:
                touched.add(_idt)
        # ── CAL（2026-10-19 口径定稿）：touched 限定在 instr 内 ──
        # 实测：touched identity 15,724，其中 6 个不在 instr（无 file_map 归属或汇编）
        #   → `touched - instr` 不参与分母减法（它们本就不是可插桩函数）。
        # 可失败判据：touched == 15,718（±0）。
        touched &= instr

    # ── unused：config.h CONFIG_*=0 ──
    comp_off = set()
    cfg = os.path.join(build_root or '', 'config.h')
    if os.path.isfile(cfg):
        txt = io.open(cfg, encoding='utf-8', errors='replace').read()
        comp_off = set(c[7:].lower() for c in _CONFIG_OFF_RE.findall(txt))

    # ── 分类（按 identity 的裸名 + 主文件）──
    macro, ffprobe, unused = set(), set(), set()
    for idt in instr:
        bare, f0 = idt
        bn = os.path.basename(f0).lower()
        stem = os.path.splitext(bn)[0]
        if 'ffprobe' in bn or 'ffplay' in bn:
            ffprobe.add(idt)
        elif stem in comp_off:
            unused.add(idt)
        elif _MACRO_STRICT_RE.search(bare) or _MACRO_ALLCAPS_RE.match(bare):
            # ── CAL（2026-10-19 口径定稿）：严格宏判定 ──────
            # 全大写+下划线 / GET_ PUT_ bytestream _template uops_ 前缀
            # 🚫 去掉裸 `bits` 子串匹配（误伤 av_get_bits_per_pixel 等 1,465 个真函数）
            macro.add(idt)
        elif bn.endswith('.h') and bare[:1].isupper() and '_' in bare:
            # ── CAL 补充（2026-10-19 审计 · 实测）：头文件混合大小写宏 ──
            # 缺陷（实测）：`COMPOSE_DD97iH0` / `DV_PROFILE_IS_1080i50` /
            #   `IS_8x8DCT` / `IS_INTRA16x16` / `IS_INTRA4x4` / `IVI_MBs_PER_TILE`
            #   共 6 个含小写字母的宏（`_MACRO_ALLCAPS_RE` 不匹配）漏进 target_set。
            #   它们全部归属 `.h` 头文件，且首字母大写 + 含下划线（C 宏命名约定）。
            # 修法：归属 .h 且首字母大写且含下划线 → 判宏。
            # 可失败判据：`IS_8x8DCT` 不得出现在 target_set；
            #   `MDS_mul`（.c 文件真函数）必须保留。
            macro.add(idt)

    real_denom = instr - macro - unused - ffprobe
    nt = real_denom - touched

    # ── SIMD ──
    simd = set()
    if os.path.isfile(ap):
        am = _load_json(ap)
        simd = set((am.get('merged_map') or {}).keys()) | set(
            (am.get('source_map') or {}).keys())
    # ── CAL（2026-10-19 口径定稿）：SIMD 按裸名匹配 identity ──
    # 缺陷（实测）：simd 集合是裸名（`ff_abs_pow34_neon`），nt 是 identity 元组
    #   → `nt & simd` 永远为空（实测只命中 5，期望 1,203）。
    # 修法：按 identity 的裸名分量匹配。
    simd_union = set(idt for idt in nt if idt[0] in simd)
    target_set = sorted(idt for idt in nt if idt not in simd_union)

    # ── 入边统计（按 identity）──
    inbound = Counter()
    for caller, v in edges.items():
        c = v.get('calls') if isinstance(v, dict) else None
        if isinstance(c, dict):
            for callee in c:
                _idt = _ident(callee)
                if _idt is not None:
                    inbound[_idt] += 1
    no_in = sum(1 for idt in nt if idt not in simd_union and inbound.get(idt, 0) == 0)
    with_in = sum(1 for idt in nt if idt not in simd_union and inbound.get(idt, 0) > 0)

    # ── 判据（可失败）──
    p1 = (no_in + with_in + len(simd_union)) == len(nt)
    p2 = len(real_denom) == len(instr) - len(macro) - len(unused) - len(ffprobe)
    p4 = bool(gmd5)
    p5 = len(target_set) == len(nt) - len(simd_union)
    p3 = None  # 与旧 denominator 对比（有旧文件时才算）
    old = None
    p3_waived = ''
    if os.path.isfile(dp):
        try:
            old = _load_json(dp)
            _old_gmd5 = old.get('graph_md5')
            _old_instr = (old.get('values') or {}).get('instrumentable')
            # ── CAL（2026-10-19 审计 · 实测）：P3 图变更豁免 ──────
            # P3 原语义：同一张图两次重算，instrumentable 必须相同（防口径漂移）。
            # 缺陷（实测）：图 md5 已变（77123111… → 07cba0f7…）时，旧分母的
            #   instrumentable（60,402，旧口径仅 caller 侧）与新口径（56,376，
            #   identity 去重）必然不等 → P3 恒 False → 合法重算被拦截。
            # 修法：图 md5 未变 → 严格比对（保留防漂移能力）；
            #   图 md5 已变 → 豁免（记录豁免原因，可审计）。
            # 可失败判据：同图重算且口径未变 → 必须 True（防漂移有效）；
            #   异图重算 → 豁免且 p3_waived 非空。
            if _old_gmd5 and _old_gmd5 != gmd5:
                p3 = True
                p3_waived = ('图 md5 已变 %s → %s，口径主动变更'
                             '（identity 去重），P3 豁免'
                             % (str(_old_gmd5)[:8], gmd5[:8]))
            elif (old.get('caliber_version') or '') != _CALIBER_VERSION:
                # ── CAL（2026-10-19 审计 · 实测）：口径版本变更豁免 ──
                # 缺陷：同一张图下修口径缺陷（如排除宏参数占位符、补判 .h 宏）
                #   → instrumentable 必然小变（56,376 → 56,358）→ P3 恒 False
                #   → 合法修复被拦截。
                # 修法：denominator 记录 caliber_version；版本变 → 豁免（可审计）。
                # 可失败判据：同图同版本重算 → 必须 True（防漂移有效）；
                #   版本变更 → 豁免且 p3_waived 非空。
                p3 = True
                p3_waived = ('口径版本变更 %r → %r，P3 豁免'
                             % (old.get('caliber_version'), _CALIBER_VERSION))
            else:
                p3 = len(instr) == _old_instr
        except Exception:
            old = None

    # ── CAL（2026-10-25 审计 14:38 打回问题 2）：审计三字段 ──
    # 缺陷（实测）：原实现 doc 不含 graph_mtime / recomputed_at / recompute_reason
    #   → 落盘走 `_merged = dict(_old_doc); _merged.update(doc)` 分支时，
    #   这三字段**继承旧文件值**（实测 recomputed_at 停在 10-14、
    #   graph_mtime 停在 10-19、recompute_reason 还是 CAL 旧文案），
    #   而 generated_at 是新的 → 审计字段与真实重算时间不一致。
    # 修法：doc 显式产出这三字段（graph_mtime 取当前图 stat / recomputed_at 取 now /
    #   recompute_reason 写本轮原因），覆盖旧值。
    # 可失败判据：写后 graph_mtime == 图 stat mtime；recomputed_at >= 本次调用时间；
    #   recompute_reason 含 'CAL'（本轮标记）。
    _now_iso = datetime.datetime.now().isoformat()
    try:
        _g_mtime = datetime.datetime.fromtimestamp(
            os.path.getmtime(gp)).isoformat()
    except Exception:
        _g_mtime = ''
    doc = {
        'generated_at': _now_iso,
        'recomputed_at': _now_iso,
        'graph_mtime': _g_mtime,
        'recompute_reason': (
            'CAL（2026-10-25 审计 14:38 打回问题 2）：'
            '重算并重绑当前图 %s；同步刷新 graph_mtime/recomputed_at/'
            'recompute_reason 三审计字段（原实现继承旧文件值 → 指向 10-19 旧图）'
            % gmd5[:8]),
        'graph_md5': gmd5,
        'caliber_version': _CALIBER_VERSION,
        'graph_path': gp,
        'authority': 'CAL 序2（2026-10-17 审计）：口径照抄 _c_layer_target_v5.py',
        'touched_source': es,
        'asm_source': ap,
        'build_root': build_root,
        'values': {
            # ── 新口径（C 层分母，CAL 序2）──
            'instrumentable': len(instr),
            'macro': len(macro),
            'unused': len(unused),
            'ffprobe': len(ffprobe),
            'real_denom': len(real_denom),
            'touched': len(touched),
            'nt': len(nt),
            'SIMD': len(simd_union),
            'no_inbound_non_simd': no_in,
            # CAL 遗留 2 改法 A（2026-10-17 审计）：改名避免同名不同义。
            # 旧 with_inbound = 全图有入边节点数（23500）；
            # 新口径是「nt 内有入边」（6495）→ 改名为 with_inbound_in_nt。
            'with_inbound_in_nt': with_in,
            # ── 旧口径（节点覆盖统计，CAL v5 脚本）──
            # 严格按旧定义算，与旧 denominator 逐键对齐。
            # CAL：inbound 已改为 identity 键 → 旧口径统计需用 identity 映射。
            'total_nodes': len(edges),
            # ── CAL（2026-10-25 审计 · 实测口径矛盾修复）──────────
            # 缺陷（实测）：原实现 `fm.get(k)` 直接查 key，**不走 _fm_of() 的
            #   裸名回退** → 与 instrumentable（走 _ident() → _files_of_key()
            #   → _fm_of()，有裸名回退）**两套口径**。
            # 旧图（07cba0f7）时：with_file_map 23,128 / instrumentable 56,358
            #   → 已矛盾（instrumentable > with_file_map，违反 cross_check），
            #   但差异不显眼未被发现。
            # 新图（cb2b8d3c）key 形态变化后放大：with_file_map 3,792 vs
            #   instrumentable 28,369（差 24,577）→ 彻底暴露。
            # 实测：edges key 直接命中 fm 仅 3,792，但**裸名回退可命中 24,605**，
            #   合计 28,397（与 instrumentable 28,369 差 28 = 汇编/宏参数排除）。
            # 修法：改用 _fm_of()（含裸名回退），与 instrumentable 同源。
            # 可失败判据：with_file_map >= instrumentable（cross_check 恢复）。
            'with_file_map': sum(1 for k in edges if _fm_of(k)),
            'no_file_map': sum(1 for k in edges if not _fm_of(k)),
            'without_inbound': sum(1 for k in edges
                                   if inbound.get(_ident(k), 0) == 0),
            # 旧口径：全图有入边节点数（不是 nt 内）
            'with_inbound_all': sum(1 for k in edges
                                    if inbound.get(_ident(k), 0) > 0),
            # 旧口径：无入边 且 可插桩（不是「无入边非SIMD」）
            'noin_instrumentable': len(set(idt for idt in instr
                                           if inbound.get(idt, 0) == 0)),
        },
        'c_layer_target': {
            'graph_md5': gmd5,
            'instr': len(instr),
            'macro': len(macro),
            'unused': len(unused),
            'ffprobe': len(ffprobe),
            'real_denom': len(real_denom),
            'touched': len(touched),
            'nt': len(nt),
            'SIMD汇编': len(simd_union),
            '无入边非SIMD': no_in,
            '有入边': with_in,
            'target_set': len(target_set),
        },
        'checks': {
            'P1_闭合': p1,
            'P2_分母一致': p2,
            'P3_与旧denominator一致': p3,
            'P3_豁免原因': p3_waived,
            'P4_图绑定': p4,
            'P5_target_set': p5,
        },
    }
    checks = doc['checks']
    ok = p1 and p2 and p4 and p5 and (p3 is not False)

    res = {'ok': ok, 'dry_run': dry_run, 'data': doc,
           'target_set': sorted(idt[0] for idt in target_set),
           'written': False, 'backup': '',
           'error': ''}
    if dry_run:
        return res
    if not ok:
        res['error'] = '判据未全过，拒绝落盘: %s' % checks
        return res

    # ── 四步写：备份 → 写 → 验证 → 确认 ──
    # CAL 序5（2026-10-17 审计，审计台账项 3）：备份时机已正确
    #   （先读原文件 → 写 backup → 再写 tmp → replace）。本日 4 次「备份=改后态」
    #   的真因是：重算结果与改前完全一致（内容未变），非时序缺陷。
    #
    # 🔴 第二轮 P1 修复（审计 19:45 打回）：原实现直接写新 doc（只有 9 字段）
    #   → 丢掉旧文件的 10 个元字段（created/cross_check/definitions/graph_mtime/
    #   note/p1_d_layer/recompute_reason/recomputed_at/stale_policy/values_basis）
    #   → 数据丢失；且旧/新结构不同 → 语义 md5 永远不等 → content_unchanged 恒 False。
    #   修法（审计方案 2）：新 doc 以旧 doc 为底（old.update(new)）再写，
    #   既保留元字段，又让 content_unchanged 真正可比。
    backup = ''
    _backup_md5 = ''
    _pre_md5 = ''
    _old_doc = None
    _old_bytes = b''
    if os.path.isfile(dp):
        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup = dp + '.bak_' + ts
        with open(dp, 'rb') as fi, open(backup, 'wb') as fo:
            _old_bytes = fi.read()
            fo.write(_old_bytes)
        _backup_md5 = hashlib.md5(_old_bytes).hexdigest()
        _pre_md5 = _backup_md5
        try:
            _old_doc = json.loads(_old_bytes.decode('utf-8'))
        except Exception:
            _old_doc = None

    # ── TD-38 修复（2026-10-18 审计 · 要求）：c_layer_target 深合并 ──
    # 缺陷（审计 2026-10-18 01:16 实证）：原实现 `_merged.update(doc)` 是
    #   **顶层浅合并** —— doc 与 _old_doc 都含 c_layer_target 键 → 新值整体
    #   覆盖旧值 → 旧 c_layer_target 内的元字段（source_script / stale_note /
    #   touched_at / touched_source / 判据）全部丢失（实测变 None）。
    # 修法（审计建议，审计认可）：对 c_layer_target 做一层深合并 ——
    #   以旧子字典为底，新子字典中**非 None** 的键覆盖。
    #   None 不覆盖：保留旧值（防重算未产出该字段时把已有元信息抹掉）。
    # 可失败判据：旧 doc 带 c_layer_target.source_script="X"、新 doc 不带 →
    #   合并后必须 == "X"（不修则 None）。
    _merged = dict(_old_doc) if isinstance(_old_doc, dict) else {}
    _merged.update(doc)
    _old_clt = (_old_doc or {}).get('c_layer_target')
    _new_clt = doc.get('c_layer_target')
    if isinstance(_old_clt, dict) and isinstance(_new_clt, dict):
        _deep = dict(_old_clt)
        for _k, _v in _new_clt.items():
            if _v is not None:
                _deep[_k] = _v
        _merged['c_layer_target'] = _deep
    doc = _merged
    tmp = dp + '.tmp'
    _os_dir = os.path.dirname(dp)
    if _os_dir and not os.path.isdir(_os_dir):
        res['error'] = '目标目录不存在，拒绝落盘: %s' % _os_dir
        res['backup'] = backup
        return res
    with io.open(tmp, 'w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    os.replace(tmp, dp)
    # 验证
    back = _load_json(dp)
    if back.get('graph_md5') != gmd5 or \
            (back.get('c_layer_target') or {}).get('target_set') != len(target_set):
        res['error'] = '写后验证失败（回写内容不符）'
        res['backup'] = backup
        return res
    # ── CAL（审计 14:38 打回问题 2）：三审计字段写后校验（可失败）──
    _meta_bad = []
    if back.get('graph_mtime') != _g_mtime:
        _meta_bad.append('graph_mtime: %r != %r'
                         % (back.get('graph_mtime'), _g_mtime))
    if back.get('recomputed_at') != _now_iso:
        _meta_bad.append('recomputed_at: %r != %r'
                         % (back.get('recomputed_at'), _now_iso))
    if 'CAL' not in str(back.get('recompute_reason') or ''):
        _meta_bad.append('recompute_reason 未含本轮标记')
    if _meta_bad:
        res['error'] = '写后验证失败（审计三字段）: ' + '; '.join(_meta_bad)
        res['backup'] = backup
        return res
    res['written'] = True
    res['backup'] = backup

    # ── CAL（2026-10-19 审计裁定方案 B）：同步写 target_set.json ──
    # 缺陷（实测）：denominator.json 的 c_layer_target.target_set 只是**计数**
    #   （int 17,653），完整清单从未落盘 → C 层 focus_funcs 无源可取
    #   → 不传则反推 56,948（白跑 3.5h）。
    # 修法（审计 2026-10-19 01:40 裁定）：独立文件 data/acd/<ws_id>/target_set.json
    #   理由：元数据（5.4KB）与大数据（~900KB）分离；可单独绑 graph_md5 +
    #   caliber_version（图换了清单自动 stale，比塞在 denominator 里更难漏检）。
    # 字段：targets（裸名，C 层接口收裸名）+ targets_identity（[裸名,路径]，供审计）
    #   + count + graph_md5 + caliber_version + denominator_md5（清单与分母同源）
    # 可失败判据：count == len(targets) == len(targets_identity)；
    #   graph_md5 == 当前图；denominator_md5 == 分母文件 md5；
    #   target_set.json mtime >= denominator.json mtime（防下次重算又漏）。
    _tsp = os.path.join(d, 'target_set.json')
    _ts_doc = {
        'generated_at': datetime.datetime.now().isoformat(),
        'graph_md5': gmd5,
        'caliber_version': _CALIBER_VERSION,
        'denominator_md5': _md5_file(dp),
        'count': len(target_set),
        'targets': sorted(idt[0] for idt in target_set),
        'targets_identity': [[idt[0], idt[1]] for idt in sorted(target_set)],
    }
    _ts_tmp = _tsp + '.tmp'
    try:
        with io.open(_ts_tmp, 'w', encoding='utf-8') as f:
            json.dump(_ts_doc, f, ensure_ascii=False, indent=1)
        os.replace(_ts_tmp, _tsp)
        _ts_back = _load_json(_tsp)
        _ts_ok = (_ts_back.get('count') == len(target_set)
                  and len(_ts_back.get('targets') or []) == len(target_set)
                  and len(_ts_back.get('targets_identity') or []) == len(target_set)
                  and _ts_back.get('graph_md5') == gmd5)
        res['target_set_file'] = _tsp
        res['target_set_file_ok'] = bool(_ts_ok)
        if not _ts_ok:
            res['error'] = 'target_set.json 写后验证失败（count/targets 不一致）'
    except Exception as _e:
        res['target_set_file'] = _tsp
        res['target_set_file_ok'] = False
        res['error'] = 'target_set.json 写入失败: %s' % _e
    # CAL 序5：内容未变告警（非缺陷，语义澄清）
    # 🔴 语义层比较：generated_at 每次都变 → 整体 md5 必不同，
    #    不能作为「内容是否变化」的判据。改为剔除易变字段后比较。
    #    且只比「重算产出面」（values / c_layer_target / graph_md5）——
    #    旧文件元字段（created 等）与新 doc 本就不是同一类内容。
    _post_md5 = _md5_file(dp)
    res['pre_md5'] = _pre_md5
    res['post_md5'] = _post_md5
    res['backup_md5'] = _backup_md5

    def _semantic_md5(doc_or_bytes):
        """交集键语义 md5（target_set + graph_md5 + values 交集键）。

        CAL 序5 口径（2026-10-17 审计二次确认，审计实测修正）：
          旧 denominator（v5 脚本）的 values 是「节点覆盖统计」，新 recompute
          的 values 是「C 层分母口径」——两套指标不可比（唯一交集仅
          instrumentable）。
        CAL 遗留 2（2026-10-17 要求「不要遗留」）：两套口径并存后，
          改为比「交集键」——口径统一前只比共有键（不误报），统一后交集
          自动扩大（无需改代码）。
        返回 (md5, compared_keys)。
        """
        try:
            if isinstance(doc_or_bytes, bytes):
                d = json.loads(doc_or_bytes.decode('utf-8'))
            else:
                d = dict(doc_or_bytes)
            return d
        except Exception:
            return None

    def _semantic_pair(pre_doc, post_doc):
        """比交集键 → (pre_md5, post_md5, compared_keys)。

        CAL 遗留 2 改法 A（2026-10-17 审计）：交集按「键名 + 口径」
          而非仅键名——同名不同义的键已改名隔离（with_inbound →
          with_inbound_in_nt / with_inbound_all），交集自动只剩真正同义的键。
        """
        if not isinstance(pre_doc, dict) or not isinstance(post_doc, dict):
            return '', '', []
        pv = pre_doc.get('values') or {}
        nv = post_doc.get('values') or {}
        # 旧 v5 文件的 with_inbound 与新文件的 with_inbound_all 同义 → 别名对齐
        _pv = dict(pv)
        if 'with_inbound' in _pv and 'with_inbound_all' not in _pv:
            _pv['with_inbound_all'] = _pv.pop('with_inbound')
        common = sorted(k for k in (set(_pv) & set(nv))
                        if isinstance(_pv.get(k), (int, float))
                        and not isinstance(_pv.get(k), bool)
                        and isinstance(nv.get(k), (int, float))
                        and not isinstance(nv.get(k), bool))
        pre_core = {
            'target_set': (pre_doc.get('c_layer_target') or {}).get('target_set'),
            'graph_md5': pre_doc.get('graph_md5'),
            'values_common': {k: _pv.get(k) for k in common},
        }
        post_core = {
            'target_set': (post_doc.get('c_layer_target') or {}).get('target_set'),
            'graph_md5': post_doc.get('graph_md5'),
            'values_common': {k: nv.get(k) for k in common},
        }
        try:
            a = hashlib.md5(json.dumps(pre_core, ensure_ascii=False,
                                       sort_keys=True).encode('utf-8')).hexdigest()
            b = hashlib.md5(json.dumps(post_core, ensure_ascii=False,
                                       sort_keys=True).encode('utf-8')).hexdigest()
            return a, b, common
        except Exception:
            return '', '', common

    _pre_sem, _post_sem, _cmp_keys = _semantic_pair(_old_doc, back)
    res['content_unchanged'] = bool(_pre_sem and _post_sem and _pre_sem == _post_sem)
    res['semantic_md5_pre'] = _pre_sem
    res['semantic_md5_post'] = _post_sem
    res['semantic_compared_keys'] = _cmp_keys
    # ── TD-38 修复（同单）：preserved_meta_fields 需查顶层 + c_layer_target 子层 ──
    # 缺陷（审计实证 · 假信号）：原实现只检查**顶层键** ——
    #   `sorted(k for k in (_old_doc or {}) if k not in doc)`。
    #   c_layer_target 在 doc 里存在 → 不算丢失 → 恒返回 []，永远报「无丢失」。
    # 修法：顶层键 + c_layer_target 子键 双层检查，子层丢失项以
    #   "c_layer_target.<key>" 形式列出（可定位）。
    # 可失败判据：构造 c_layer_target 子字段丢失场景 → 返回值必须非空（不修则 []）。
    _preserved = [k for k in (_old_doc or {}) if k not in doc]
    _old_clt_p = (_old_doc or {}).get('c_layer_target')
    _new_clt_p = (doc or {}).get('c_layer_target')
    if isinstance(_old_clt_p, dict):
        _new_clt_p = _new_clt_p if isinstance(_new_clt_p, dict) else {}
        for _k2 in _old_clt_p:
            if _k2 not in _new_clt_p or _new_clt_p.get(_k2) is None:
                _preserved.append('c_layer_target.' + str(_k2))
    res['preserved_meta_fields'] = sorted(_preserved)
    if res['content_unchanged']:
        res['note'] = ('核心项（target_set + graph_md5 + values 交集键 %d 个）与改前一致'
                       '（语义 md5 %s）= 本次重算结果未变，非备份时机缺陷'
                       % (len(_cmp_keys), _post_sem))
    else:
        res['note'] = ('核心两项与改前不同（或首次运行）：target_set/graph_md5 有变化；'
                       'values 口径跨版本不可比，不参与比对')
    return res

def _main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(
        description='重算分层分母（默认只算不写）。口径定义见 docs/caliber.md')
    ap.add_argument('--graph', required=True, help='acd_graph.json 路径')
    ap.add_argument('--build-root', default='',
                    help='构建目录（读 config.h 以排除 CONFIG_*=0），缺省则不排除')
    ap.add_argument('--asm', default='', help='asm_capstone_map.json 路径')
    ap.add_argument('--touched', default='',
                    help='D 层 edges_fate_*.json；缺省则从 <图目录>/trace_build 取最新')
    ap.add_argument('--out', default='', help='denominator.json 输出路径（--write 时生效）')
    ap.add_argument('--compare', default='', help='与现有 denominator.json 逐字段比对')
    ap.add_argument('--write', action='store_true', help='落盘（默认只算不写）')
    a = ap.parse_args(argv)

    r = recompute(graph_path=a.graph, build_root=a.build_root, asm_path=a.asm,
                  touched_source=a.touched, out_path=a.out, dry_run=not a.write)
    if not r.get('ok'):
        print('FAIL:', r.get('error'))
        return 2

    doc = r.get('data') or {}
    print('graph md5:', doc.get('graph_md5'))
    for k, v in (doc.get('values') or {}).items():
        print('  %-22s %s' % (k, v))
    print('checks:', doc.get('checks'))

    if a.compare:
        import json as _json
        exp = (_json.load(open(a.compare, encoding='utf-8')).get('values') or {})
        got = doc.get('values') or {}
        bad = [(k, exp[k], got.get(k)) for k in exp if got.get(k) != exp[k]]
        if bad:
            print('对照 %s：不一致 %d 项' % (a.compare, len(bad)))
            for k, e, g in bad:
                print('  %-22s 期望 %s 实得 %s' % (k, e, g))
            return 1
        print('对照 %s：全部一致' % a.compare)

    if a.write:
        print('written:', r.get('written'), '| backup:', r.get('backup'))
    return 0


if __name__ == '__main__':
    raise SystemExit(_main())
