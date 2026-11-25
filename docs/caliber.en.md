# Caliber & Limits

> **中文** → [`caliber.md`](caliber.md)
> The definitions, the known limits, and the rules behind every number in this repository.
> Numbers live in exactly one place: [`data/denominator.json`](../data/denominator.json). This file holds **no value tables** — by design.

This document answers the question a real reader asks: **why should these numbers be trusted, and where exactly are they wrong.**

It contains only **definitions, boundaries and discipline** — no value tables. The single source of values is [`data/denominator.json`](../data/denominator.json) (built together with graph `b357bf8e…`, shipped inside the same release package). **The same number appearing in two places in this repository is a defect.**

---

## 1 Five rules

### 1.1 Single source of truth
One metric = one definition + one denominator + one data source. A metric definition scattered across several places is a violation.

### 1.2 No subtraction or division across calibers
Different numerator and denominator calibers → no division; no subtraction. If the same denominator genuinely has to be reused, say explicitly "this reuses the same denominator" instead of assuming it holds.

The two easiest traps in this repository:
- "edges from the primary source" and "exclusive contribution" are different calibers and **must not be added** (see the note under the source-breakdown table in README);
- `target_set` and `touched` are not the same set and **must not be divided directly**.

### 1.3 Evidence hierarchy
`runtime code (runtime) > static syntax > registry inference > LLM inference`

Any disagreement is marked `unobserved`: **never deleted, never merged, never guessed**. Any edge count or reach rate given to the outside must come with its source distribution, not just a total.

### 1.4 Caliber name is mandatory
Quoting a number requires the full caliber name. **Writing bare "coverage", "no inbound", "dead code" is a violation**, because every word here has at least two calibers (see §2.5–§2.6).

### 1.5 Anchors and staleness
Every derived number is bound to a graph anchor (md5). **Graph md5 changes → every derived number is stale, quoting must stop, recomputation is required.** See §8.

---

## 2 Terms and definitions

### 2.1 `pk` (the target_set match key)
```
pk(n, f) = n + '@ffmpeg-src#' + norm(f).replace('/', '#')
norm(f)  = strip the 'ffmpeg-src/' prefix
```
`norm` is not optional: file paths in the target list come in two forms (with and without the `ffmpeg-src/` prefix). Without normalization you build double-prefixed keys `name@ffmpeg-src#ffmpeg-src#…` and **every target is misjudged as a gap**.

Matching must use the `[name, file]` pair, **never a list of bare names** — there `file` is empty and the gap count inflates by an order of magnitude.

### 2.2 Three forms of a key

| Form | Example | Nature |
|:--|:--|:--|
| With workspace prefix | `name@ffmpeg-src#dir#file` | canonical form |
| Without workspace prefix | `name@dir#file` | early defect, already fixed (currently 0) |
| Bare name | `name` | by design: multi-copy aggregation / external symbols |

### 2.3 Three tiers of `target_set`

| Tier | Test |
|:--|:--|
| **A** already a caller node | `pk(n,f)` is in the `edges` key set |
| **B** appears only as a callee | not in the key set, but appears as a callee in some `calls` |
| **C** true gap | neither caller nor callee |

### 2.4 Three forms of `callee_id`

| Form | Test | Nature |
|:--|:--|:--|
| exact key | contains `@` and `#` | BFS-able |
| bare name | contains no `#` | by design (no ID written) |
| empty | `null` | external symbol / intentionally empty (see §3) |

### 2.5 Two calibers for "no `callee_id`"

| Caliber | Definition | Use |
|:--|:--|:--|
| **strict** | `callee_id ∈ edges.keys()` | **all verification uses the strict caliber** |
| loose | normalizing to an exact key is allowed | attribution only, never for decisions |

The loose caliber hides problems, so any "consistency rate" must state which one it used.

### 2.6 Four calibers for "no inbound edge" (**four numbers, four definitions, never mixed**)

| Caliber | Definition | Nature |
|:--|:--|:--|
| ① raw string | the key never appears as a callee of any edge | direct graph computation |
| ② bare-name normalization | a bare name is referenced, **or** any exact key of the same bare name is referenced, counts as having inbound | direct graph computation (must expand to exact keys) |
| ③ identity dedup | same name in the same file counted once | direct graph computation |
| ④ denominator-tool caliber | `without_inbound_identity` output by the denominator tool | tool caliber, includes asm / bare-name fallbacks |

> The difference between ① and ② is not a defect; it is "do we acknowledge bare-name references". ② must **expand to exact keys of the same bare name**; only excluding "the bare name itself is referenced" undercounts — that is a wrong implementation.
> The gap between ④ and ①②③ comes from fallback logic inside the tool and **is not an arithmetic error**.

When quoting a no-inbound number externally, the caliber number or full name is mandatory.

### 2.7 The denominator chain

```
total_nodes    = len(edges.keys())
with_file_map  = has file_map (full_id first, fall back to bare name)
instrumentable = has file_map and is not assembly (dedup by name+file)
real_denom     = instrumentable − macro − unused − ffprobe
touched        = reached by layer-D traces (restricted to instrumentable)
nt             = real_denom − touched          ← set difference
target_set     = nt − SIMD
```

The **reach rate** (not called "coverage", see §11) has **two calibers, and both must be stated**:

| Caliber | Formula |
|:--|:--|
| the only public caliber | `touched / instrumentable` |
| tightened caliber | `touched / real_denom` |

**Field coverage and synonyms**: `values` in `data/denominator.json` has 16 fields but `definitions` writes a definition for only 12 of them; the missing 5 are defined below (same source as report §6.2.2). Two synonym pairs: `values.with_inbound_all` = `definitions.with_inbound`; `values.total_nodes` = `definitions.total_nodes_graph`. Values live only in `data/denominator.json` and are not repeated here.

| Field | Definition |
|:--|:--|
| `macro` | nodes whose macro name was mistaken for a function (excluded) |
| `unused` | code paths not enabled (excluded) |
| `ffprobe` | ffprobe-only, outside this graph's library caliber (excluded) |
| `real_denom` | `instrumentable − macro − unused − ffprobe` |
| `touched` | functions reached by layer-D traces inside `instrumentable` |

### 2.8 Hidden calibers in the denominator (read this when recomputation disagrees)

`instrumentable` is not a naive "nodes with file_map minus assembly nodes": it includes **deduplication by name+file**, so a naive computation overshoots by several hundred.

`nt` is a **set difference, not a numeric difference**:
```
nt = |real_denom − touched|      ← correct
nt = |real_denom| − |touched|    ← wrong
```
The difference between the two comes from a small group where "the touched set contains elements outside `instrumentable`" — macro artifacts, by design.

### 2.9 Four classes of self-recursion (the test must be language-aware)

| Class | Test |
|:--|:--|
| **true recursion** | an independent self-call statement exists in the body |
| structurally undecidable | only address-taking / assignment to a field, no self-call |
| filterable | the call form of that symbol appears 0 times in the file |
| unlocatable | bare-name node with no source path |

The test must dispatch by language, otherwise assembly self-loops are killed by mistake:

- `.s` / `.asm` → jump instruction form (`b` / `bl` / `bne` / `beq` / `b.<cond>` / `jmp` / `call` / `j*` followed by a label)
- `.c` / `.h` → `sym(` while excluding "definition line / address-taking `&sym` / assignment `= sym` / field assignment `.field = sym`"

> **Fail-able negative case**: a recursive label in an assembly file (`bne <self>`) must land in "true recursion", never in "filterable". Using only the C form gets it wrong.

### 2.10 Definition of a defect

See §3.

### 2.11 The physical limit of strict self-recursion

Instrumentation only sees "**function entry address + call-site address**" and **cannot see the call instruction itself**, so it cannot tell "true recursion" from "called indirectly through a function pointer".

Telling them apart requires **instruction-level disassembly** (parsing each call site), hours of work plus large memory for a negligible payoff → not fixed. This is why the "structurally undecidable" class exists and **is not counted as a defect**.

### 2.12 `matched_rate` (cross-confirmation rate)

> **Caliber name**: `matched_rate`. Quotes must carry this name; never write "cross-confirmation rate X%" bare.

Definition: of the runtime edge set `R`, how many have the same edge (identity granularity) on the static side.

```
S = static-family edges: sources contain static or static-reg, and not asm
R = runtime edges: sources contain runtime
matched_rate = |R ∩ S| / |R|        identity granularity = key's name@file
```

**This section deliberately gives no value table** (per the rule at the top). Three things live in exactly one place:

| What | Single location |
|:--|:--|
| expected value / tolerance constants | `EXP` in `scripts/verify_matched_rate.py` |
| recomputation command | `python scripts/verify_matched_rate.py <graph>` |
| narrative and tables in the report | `report/ACD-ffmpeg-report-v4.0.en.md` §5.1 |

Two closures that hold structurally (independent of values, still true for a different graph):

```
|R| = |R ∩ S| + |runtime only|
|S| = |R ∩ S| + |static only|
```

**Coordinate discipline**:

- not precision / recall — it only says "static also believes this edge exists", not "this edge is certainly right";
- never divided by or compared with the reach rate or the anchoring rate (different axes; similar values are coincidence);
- "static only" **is not a static error**: it contains both "registered but never called" and "not covered by tests", not individually classified.

> **Negative case (must be able to fail)**: when join is degraded to bare-name granularity the rate must differ. If both granularities give the same number, identity granularity is not in effect and the test is void.

---

## 3 What counts as a defect

Only one of the following makes a defect:

| # | Condition |
|:--:|:--|
| 1 | **breaks call-chain correctness**: an edge points at the wrong callee, upstream/downstream relations wrong |
| 2 | **causes consumer misjudgement**: e.g. matching by exact key fails, or fallback semantics taken as a wrong value |

None of the following **is a defect** (correct-by-design behaviour / mechanism ceiling):

| Item | Why not fixed |
|:--|:--|
| external symbols without file_map (`abort` / `usleep` / `__builtin_clz` / Win32 / COM) | no source code, cannot be registered |
| same name in different files not guessed | not guessing is correct; guessing mis-connects |
| `file_map[bare name]` single value | fallback semantics, not "the copy you wanted" (see §10.2) |
| bare-name nodes carry no caller/callee_id | by design |
| `callee_id` empty | bare name + external symbol; both sources are by design |
| true-recursive self-loop | the runtime layer records it correctly |
| reach rate below 100% | mechanism ceiling of the runtime layer (edges only from running tests) |
| registry edges whose callee is a "table → member" string | structurally impossible to add an in-edge to a function node |
| low assembly-layer reach | the real state (most assembly symbols are true leaf functions) |
| a leaf function with 0 inbound | attribution is correct; the source call site was not parsed into that form |

> **Reporting a "defect" against this standard = producing invalid rework.** This repository would rather publish its boundaries than dress them up as a to-do list.

---

## 4 The six `gap_class` values

Every node on the graph carries a `gap_class`. It is **not a defect marker**; it is the attribution label for "why this node has no inbound edge".

| `gap_class` | Definition |
|:--|:--|
| `HAS_INBOUND` | has inbound (static / runtime / assembly / registry, any of them) |
| `DEAD_SUSPECT` | no inbound + has file_map + not asm/SIMD + **DSP naming pattern** (`*_c` / `*_<digits>` / `avg_*` / `put_*` / `pred*` / `dc_*` / `add_*` / `sub_*` / `mul_*` / `ssd_*` / `sad_*`) |
| `UNKNOWN_DYNAMIC` | no inbound + has file_map + not asm/SIMD + not DSP naming + **inside the instrumentable set** (candidate function-pointer table member) |
| `UNCOVERED` | no inbound + has file_map + not asm/SIMD + not DSP + outside the instrumentable set (unexplained) |
| `UNKNOWN_ASM` | no inbound + assembly path (`.asm` / `.S`) or bare name hitting the assembly symbol table |
| `NO_FILE_MAP` | no inbound + file_map misses (both full_id and bare-name fallback miss) |

**Why six classes and not five**: under the four mutually exclusive and exhaustive classes `UNCOVERED` is 0 by construction (a node with file_map and no inbound must fall into either `UNKNOWN_DYNAMIC` or `DEAD_SUSPECT`). The viewer legend therefore shows only 5 colours. **It is not a missing class; that class is currently empty.**

**File attribution caliber**: to decide "which file a node belongs to", `gap_class` uses `full_id first, fall back to bare name` and **not exact-key lookup**. Because `file_map` does not cover all disambiguating keys (thousands of nodes have exact keys without an entry while the bare name does), exact-key lookup diverges from the denominator caliber.

**Three-level closure (each level can fail)**
1. whole-graph level: sum of the five no-inbound classes = total nodes − `HAS_INBOUND`
2. target-set level: `nt − SIMD − with_inbound_in_nt = no_inbound_non_simd` — this is an internal derivation of the denominator tool, **not counted from `gap_class`**
3. has-inbound level: `HAS_INBOUND = total nodes − sum of the five no-inbound classes`

> If level 2 were changed to "count directly from `gap_class`", it would differ from the denominator value by several dozen. The root cause is that the two SIMD tests have different sources (one uses a self-computed SIMD set, the other the assembly symbol table intersection); **both are correct and neither can refute the other**.

The distribution for the current graph (`b357bf8e`) can be read directly in the viewer legend; the machine-readable values ship with [`data/denominator.json`](../data/denominator.json).

---

## 5 Known limits (8 of them, not fixed)

| # | Limit | Why not fixed |
|:--:|:--|:--|
| 1 | strict self-recursion (count varies with the graph) | overwhelmingly true recursion, recorded correctly by the runtime layer; the few others need instruction-level disassembly, cost far above benefit |
| 2 | bare-name callees without file_map | external symbols (`abort` / `usleep` / `__builtin_clz` / Win32 / COM), no source |
| 3 | bare-name callees in multiple files | same name, different files; not guessing is correct |
| 4 | bare-name nodes without caller_id | by design: bare-name nodes carry no ID |
| 5 | reach rate below 100% | mechanism ceiling of the runtime layer (edges only from running tests) |
| 6 | registry edge shape (callee is "table → member") | structurally impossible to add an in-edge to a function node |
| 7 | low assembly-layer reach on x86 | the real state: most assembly symbols are true leaf functions with no caller |
| 8 | a few leaf functions with 0 inbound | file_map attribution is correct; the source call site was not parsed into that form |

> The nature of these limits does not change with the graph; the count of each does, so this table **lists no values** — look them up in `denominator.json` or recompute on the spot.

---

## 6 Why the registry layer (layer C) is frozen

The registry layer (inferring from function-pointer tables) showed very low measured payoff: **36 fillable points**, i.e. **0.32%** of the **11,216 registry candidates** and **0.031%** of the **114,175 edges in the whole graph**; a full rebuild takes 90–100 minutes, changes the graph md5, and forces every caliber binding to be re-anchored.

**The freeze comes with a fail-able criterion**: anyone wanting to reopen this layer must first show "fillable points ÷ registry candidates > 1%"; it is currently **36 / 11,216 = 0.32%**, below the bar, so it stays closed.

> Do not mix the denominators: **36 / 11,216 = 0.32%** (fillable points over registry candidates — the freeze criterion), **36 / 114,175 = 0.031%** (over all graph edges), **5 / 14,668 = 0.03%** (the historical C-layer closing rate: 5 of 14,668 reported points closed). Separately, **92 / 2,727 = 3.37%** (all candidate gaps over member-function-pointer call sites, including false positives and platform-specific code — not the "fillable" surface) and **36 / 2,727 = 1.32%** (fillable points over the same denominator); see report §6.

> The existence of that criterion matters more than the conclusion itself — it turns "not doing it" into a refutable claim instead of an attitude.
>
> There is also a recorded misjudgement: someone once used the candidate count from an **earlier round's artifacts** (305) as the current value (measured 11,216) and concluded "the payoff is substantial". **Recompute on the spot before quoting this layer's numbers; never infer backwards from historical artifacts.**

---

## 7 Not done (listed honestly)

| Item | Status |
|:--|:--|
| registry-layer LLM edge completion | this round `use_llm=false`, **LLM edges = 0**, not run |
| runtime-layer extension (new fate cases) | to be assessed |
| toolchain versions recorded | compiler / linker / capstone versions are not written into the artifacts, to be added (see [`reproduce.md`](reproduce.md)) |

---

## 8 Why two graph anchors coexist (and the staleness rule)

| Anchor | Time | Note |
|:--|:--|:--|
| `d690c09e…` | 2026-11-11 | the build the report body was written against |
| `b357bf8e…` | 2026-11-14 | files from the same build were rewritten, bytes +279 B, md5 changed |

Those 279 bytes touch only **metadata fields of cross-language edges**; node count, edge count and target set are **identical item by item**, and the 16 self-consistency checks pass 16/16 on the new graph.

```
graph md5 ≠ the anchor in this document  →  every derived number is stale  →  quoting forbidden, recompute required
```

The checking order is always: **compare md5 first, then read the numbers.** Numbers disagreeing while md5 matches → a recomputation-method problem; md5 differing → all numbers are void, no explanations.

---

## 9 Recorded misjudgements (these actually happened)

Every one of these was stepped in once and caught. They are written down because they show where this caliber's boundaries lie better than any achievement:

| Misjudgement | Truth |
|:--|:--|
| using the assembly symbol table entry count (7,420) as "the number of assembly nodes in the graph" | assembly nodes in the graph are **nodes whose key ends in `.asm`/`.S`**; different calibers, thousands apart |
| judging `callee_id` as unacceptable by the "overall consistency rate" | empty values are by design; only the **non-empty consistency rate** may be used |
| reporting "`file_map[bare name]` single value misplaces thousands of nodes" | the bare-name entry is **fallback semantics**, not "the copy you wanted"; disambiguation goes through the family index |
| counting the target-set no-inbound number from `gap_class` to refute the denominator tool | the two SIMD tests have different sources, dozens apart, **both correct** |
| using an earlier round's artifacts as the current value | candidate counts per layer vary with the graph; always recompute on the spot |

---

## 10 Consumer notes

### 10.1 Always `json.load`, never byte diff
The graph serialization format has changed between versions: one generation was compact (about 60 MB), the current one is indented and readable (about 106 MB). **A byte diff mistakes a "format change" for "everything changed"**. Parse first, then compare structures (node set / `calls` key set / top-level fields).

### 10.2 Three meanings of "look up the definition file"

| What you want | What to query |
|:--|:--|
| the definition file of one **specific copy** | `file_map[exact key]` |
| whether the symbol **exists at all** / any valid definition | `file_map[bare name]` (fallback semantics) |
| **disambiguation to the right copy** | the family index (match by caller file); do not guess from the bare name |

### 10.3 An empty `callee_id` is a normal state
Empty values have exactly two sources: bare-name callees (no ID written) and external symbols (no node to point at). To judge "is this edge pointing right", look only at the **non-empty part**.

---

## 11 Wording discipline

In outward-facing text the following phrasings are forbidden:

| Forbidden | Say instead |
|:--|:--|
| "coverage X%" (confused with gcov line/branch coverage) | "function **reach rate** X% (`touched / instrumentable`)" |
| "reach rate 100%" | "X% reached; unreached nodes attributed class by class in `gap_class`" |
| "supports C" | "validated on FFmpeg 9.1-dev / MinGW-w64 / x86_64" |
| "the call graph is complete" | "X% covered + five-class attribution of the uncovered part" |
| "dead code" | "`DEAD_SUSPECT` (suspected, unproven)" |
| "parsing is all correct" | "N self-consistency checks all pass; implicit limits in §5" |
| "all problems fixed" | "the 8 known limits remain, reasons in §5" |

---

## 12 Recompute it yourself

```bash
# 16 self-consistency checks (16/16 PASS expected on the current graph)
python scripts/verify_graph.py acd_graph.json

# recompute the reach-rate denominator from scratch (compute-only by default; --write persists)
python scripts/denominator_recompute.py \
  --graph acd_graph.json --build-root <build dir> \
  --asm <asm_capstone_map.json> --touched <edges_fate_*.json> \
  --compare data/denominator.json

# re-export the viewer views
python scripts/export_views.py --graph acd_graph.json
```

Denominator recomputation uses the three exclusion lists in `data/denominator_excluded_lists.json` (macro / unused / ffprobe) — without them the denominator can only be trusted, not computed.

Always compare values against `data/denominator.json`, not against this document — this document deliberately contains no value tables.

---

**License**: this document shares the license of `report/` (CC BY 4.0, attribution required, keep the graph md5 and commit). The scripts are MIT. See [`LICENSE`](../LICENSE).
