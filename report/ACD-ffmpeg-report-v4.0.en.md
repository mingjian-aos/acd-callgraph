# ACD Multi-Source Merged Call Graph · v4.0 (Public Open-Source Edition)

> **v4.0 revision (2026-11-24)**: terminology unified from "three layers / six sources" to **multi-source**; the graph anchor now lists both "on-disk / release anchor `b357bf8e`" and the report-body original anchor `d690c09e` (marked as not shipped with the repo or the package, not publicly available); denominator and target-set fingerprints updated to the recomputed artifacts (`616cb5e3` / `5633cb3a`). **Aggregate numbers unchanged.**
> **Subject**: FFmpeg (x86_64 / Windows / MinGW-w64)
> **Data tagging**: `[measured]` = read directly from an artifact, with the data-source field given; `[derived]` = computed from measured data, with the formula given. Items that cannot be recomputed are **explicitly marked not recomputable**; no estimates are filled in.
> **Verification stance**: every aggregate number in this report was **recomputed on the spot** from `acd_graph.json` / `denominator.json` (each `edges` entry walked, each `sources` array expanded), **never transcribed from another document**. Wherever a document record disagrees, the on-the-spot recomputation in this report governs, and the cause of the difference is noted.

---

## 0. Scope: what this tool is, and what it is not

**What it is**: a construction-and-quantification tool for a **function-level call graph**. It answers three questions — **who calls whom, who else calls them, and which line issued the call**.

**What it is not** (equally important):

| Not | Explanation |
|:--|:--|
| ❌ Not a coverage tool | This tool **does not produce** line or branch coverage. Use gcov for line/branch coverage. |
| ❌ Not a gcov substitute | The two **measure different objects** (see §7); they are not two algorithms for the same thing. |
| ❌ Does not claim "more precise / higher quality" | No such evidence exists in this version (edge precision has not been sampled, see §6 #1). |

### Three usage prohibitions (apply throughout)

1. **No subtraction**: never compute "a gap of X percentage points" between this tool's numbers and official coverage
2. **No division**: no multiple/factor comparisons
3. **No ranking / no side-by-side comparison tables**

### 0.1 Version anchors (reproduction prerequisites)

| Item | Value |
|:--|:--|
| Source commit | `818cecc6e1afab932cf4d40ef0d7b8cd40311a17` (2026-08-30 16:03 UTC, clean work tree) |
| **Graph anchor md5 (report-body original)** | **`d690c09ef8f148091e95871452a77259`** (106,072,360 B / 2026-11-11T00:05:58; not shipped with the repo or the package) |
| **Graph anchor md5 (on-disk / release)** | **`b357bf8ea8a4b6bae4892ab99254bf2a`** (106,072,639 B / mtime 2026-11-14T18:04:37) |
| Graph file size | 106,072,639 B (on-disk; the original report-body anchor was 106,072,360 B — a 279 B difference, cross-language metadata only) |
| **Graph creation time** (`generated_at`) | **2026-11-11T00:05:58** |
| File mtime | 2026-11-14T18:04:37 (on-disk) |
| **Build parameters** | `incremental=false` (full rebuild) / `use_llm=false` (Layer C frozen, see §3.6) |
| Build artifact | `ffmpeg.exe` (127 MB, **full DWARF retained**: `.debug_info` 4 MB / `.debug_line` 8.9 MB) |
| Denominator authority | `denominator.json`, md5 **`1da5867bafdede493bb3901e4bd7c4a5`** (1,955 B, **redacted distribution copy**, shipped with the repo / inside the release package); the audit original `616cb5e3…` (7,366 B, with audit fields, not shipped) is **field-for-field identical in value** to the distribution copy; bound to `b357bf8e` |
| Target set | `target_set.json`, md5 **`5633cb3add38fe2210ad09128b627526`** (rewritten 2026-11-15, 14,375 entries unchanged), bound to this same graph |
| Runtime data | `trace_build/edges_fate_20261013_192424_recover.json` (`meta.runtime.status = reused` — rebuilding the graph does not change runtime behaviour; FATE was not re-run in this round) |

> **The graph md5 is the binding key for every number in this document.** Numbers from any graph whose md5 differs must not be mixed with this report.
> If the build artifact is `strip`ped, the address-resolution capability in §3.3 is lost (see §6 #9).
> **Reproduction prerequisites**: full build (`incremental=false`) + Layer C off (`use_llm=false`) + DWARF retained. Missing any one of the three and the numbers are not reproducible.

---

## 1. The three questions it answers

### 1.1 "Which functions still have callers, but were not reached by tests?" → **14,375 supplementary-test candidates** `[measured]`

| Category | Count | Meaning |
|:--|--:|:--|
| No inbound edge, non-SIMD | 6,232 | No caller inside the graph (function-pointer-table candidates) |
| **Has inbound edge but not reached** | **8,143** | **Still called, but not covered by tests → highest supplementary-test priority** |
| SIMD assembly | 1,223 | Assembly implementations, handled separately |
| Untouched total `nt` | 15,598 | `= 6,232 + 8,143 + 1,223` |
| **Supplementary-test target set `target_set`** | **14,375** | `= 6,232 + 8,143` |

Data source: `denominator.json → c_layer_target`. Closure check: `6,232 + 8,143 + 1,223 = 15,598` ✅

> **✅ Reproducibility of this number**: `target_set 14,375` and its 11 upstream denominator fields **have been independently recomputed field by field under this repository's definitions ([`docs/caliber.md`](../docs/caliber.md)), and all agree** (see **§6.2.2**). The three exclusion lists ship with the repo (`data/denominator_excluded_lists.json`, §6.2.3). The known boundary cost is 8 entries (0.056%), disclosed in §6.2.4.

> **This is the core difference from tools that only report "not reached"**: this tool can say "**which ones still have callers**", turning an uncovered list into a list **with structural information**.

**🔴 What `8,143` actually means (important — do not read it as "supplementary tests will cover these")** `[measured]`:

`8,143` is a **structural fact inside the graph** — these functions have inbound edges in the call graph, but a single FATE run did not reach them. **It does not mean "just add tests and coverage follows"**. We tested that hypothesis:

| Check | Measured result |
|:--|:--|
| Attempted supplementary tests for these 8,143 functions | sampled **2,492** |
| Supplementary-test hits (new coverage) | **0** |
| Remaining unverified | **5,651** (**not extrapolated to "all invalid"**) |

> **Interpretation**: 2,492 sampled with 0 hits means the **main reason for "inbound but unreached" is not missing tests**, but more likely platform differences (`#ifdef`), configuration gating (`CONFIG_*`), or a need for specific input conditions. **Until the cause is established, these 8,143 should not be dispatched directly as "supplementary-test tickets".**
>
> This also corrects a common misreading: **`target_set` is the set "structurally worth attention", not the set "supplementary-test benefit already proven".** We paid the verification cost of 2,492 samples to establish that difference.
>
> **The two categories are handled differently**: `8,143` (has inbound) needs **classification before dispatch**; `6,232` (no inbound) are mostly function-pointer-table members, identified via the registry (`static-reg`) rather than by supplementary tests — **even less suited to being ranked by supplementary-test priority**.

### 1.2 "Where did this edge come from?" → **layered attribution, 114,175 edges** `[measured]`

| Layer | Edges (`source` basis) | Semantics | Usage limit |
|:--|--:|:--|:--|
| `static` | 55,539 | confirmed by static parsing | base layer |
| `runtime-confirmed` | 45,187 | **actually happened** (FATE instrumentation trace) | primary |
| `static-reg` | 8,571 | **registration possibility** (function-pointer-table members) | **must be labelled "possible", not an actual call** |
| `asm` | 4,878 | assembly parsing | no instrumentation point |
| `llm` | 0 | frozen (see §3.6) | design state |
| **Total** | **114,175** | — | **never to be quoted as "number of actual call edges"** |

**Confidence**: `30,259` edges (**26.50%**) are cross-confirmed by **≥2 independent sources**; `83,916` are single-source only.
Closure check: `83,916 + 30,259 = 114,175` ✅

**Unique contribution (two different bases — do not extrapolate one from the other)**:

| Quantity | Value | Definition |
|:--|--:|:--|
| Three-**path** unique total | **28,379** | runtime 16,362 + asm 3,446 + static-reg 8,571 (baseline = 0 for the layer) |
| Merged vs strongest single layer | **28,426** | 114,175 − 85,749 (baseline = edges containing static, 85,749; the static-primary basis is 55,539) |

> ⚠️ That the two numbers are close (differ by 47) is coincidence; they are **two different quantities**: the first measures "the unique part contributed by the layers together", the second measures "the gain of merging over a single source". **Do not merge them, do not cite one for the other, do not derive one from the other.**

> The full breakdown of each layer's unique edges is in **§2.1** (this section gives the summary only).

### 1.3 "Which line issued the call?" → **call-site line anchoring for 18,898 edges (68.48%)** (old anchor `d690c09e`; not a current-data conclusion) `[measured]`

This capability is new in this version:

> gcov can say "line 1051 executed 5,912 times", but **cannot say which function that line called**.
> This tool anchors the **source-line call site** and the **runtime call address** onto the same edge, yielding "**which line → calls whom → how many times**".

| Item | Value |
|:--|--:|
| Anchorable edges (both static `call_sites` and runtime `call_site_addr` non-empty) | **27,596** |
| Line numbers agree | **18,898** |
| **Line-level anchoring rate** | **68.48%** |

Data source: `callsite_coverage.json → call_site_line_anchor`

> 🔴 **Anchor note**: this data source is bound to `d690c09e`, and its `edges` (static 78,425 / runtime 45,198 / matched 35,562) are exactly the set that §5.1 declares **void**; the 27,596 comparable edges and the 18,898 line agreements are all computed inside that old matched set. **It is not a current measurement on `b357bf8e`** — do not mix it with §5.1's 63.7% (identity) or the 68.4% bare-name join.

> ⚠️ **Recomputability**: this item depends on `callsite_coverage.json` (an internal audit artifact, not shipped in the repo or the Release) and on a `ffmpeg.exe` **with DWARF**, so it **cannot be recomputed from `acd_graph.json` alone**. The nearest recomputable quantity inside the graph is "static edges carrying `call_sites` = 79,873 (69.96%)" — the two **are not the same quantity and must not be converted into each other**.

> ⚠️ The 8,698 unanchored edges **have not been classified one by one** (known causes include "static parsing recorded only some call sites" and "macro expansion shifts line numbers"). This 68.48% **is not comparable with any other ratio**.

---

## 2. Why merging is necessary (★ this chapter is the core)

> **This chapter answers**: single-layer call graphs (pure static / pure dynamic) are mature industry practice, so **where exactly is the incremental value of multi-layer merging?**
> **Data source**: `acd_graph.json → edges`, per-edge `source` / `sources` fields, recomputed on the spot (read-only).
> **Basis**: this chapter uses the `sources` (all-sources) basis throughout, which **differs from the `source` (primary-source) basis of §1.2 and must not be mixed**; see §3.7.

### 2.1 Irreplaceability of each layer (unique edges) `[measured]`

> **Definition**: a layer's "unique edges" = call edges that layer can find and **no other layer can find**.
> **Basis**: key = `(caller, callee)` pair; **unique = the edge's `sources` set has exactly size 1**.

| Layer | Edges in layer (`sources` basis) | **Unique edges** | Unique rate | Note |
|:--|--:|--:|--:|:--|
| **static** | 85,749 | **55,537** | 64.8% | static-parsing base |
| **runtime** | 45,187 | **16,362** | **36.2%** | 🔴 **dynamic calls static cannot see** (function pointers / callbacks / dynamic dispatch) |
| **asm** | 4,921 | **3,446** | **70.0%** | 🔴 **assembly calls C parsing cannot see** |
| **static-reg** | 8,619 | **8,571** | **99.4%** | 🔴 **function-pointer-table registration edges** |
| **llm** | 0 | **0** | — | frozen (§3.6) |
| **Unique total** | — | **83,916** | — | no single layer can cover this |

**How to read this table**:

- **runtime's 36.2% unique rate** is the hardest piece of value in merging: these 16,362 edges are **unobtainable by static parsing in principle** (the compiler cannot see a call target that is decided at runtime).
- **static-reg's 99.4% unique rate** shows that function-pointer tables lie almost entirely in other layers' blind spots (reason in §2.5 — **not a data error**).
- **asm's 70.0% unique rate** shows that assembly calls are a structural blind spot of C-level parsing.
- ⚠️ "Unique" and "cross-confirmed" are **two sides of the same coin**: a unique edge is single-source by definition, so it **cannot** be cross-confirmed. A high unique rate therefore does not mean low confidence — it means **strong complementarity**.

### 2.2 Merge gain `[measured]`

| Item | Value |
|:--|--:|
| Strongest single layer (static, `sources` basis) | 85,749 |
| **Edges after merging** | **114,175** |
| **Gain** | **+28,426 edges (+33.1%)** |

**⇒ Relative to the strongest single method, multi-layer merging raises edge coverage by 33.1%.**

> Note on basis: the comparison baseline here is **this tool's own single layer**, i.e. "merged vs not merged", **not** a comparison against any external tool.

### 2.3 Multi-source cross-confirmation (confidence tiers) `[measured]`

> **Definition**: the same `(caller, callee)` edge confirmed simultaneously by **several independent methods** → confidence far above a single-source guess.

| Confirmed by | Pairs | Share |
|:--:|--:|--:|
| 1 source | 83,916 | 73.50% |
| **2 sources** | **30,217** | **26.47%** |
| 3 sources | 42 | 0.04% |
| **⇒ ≥2 sources (primary basis, including static-reg)** | **30,259** | **26.50%** |
| ⇒ ≥2 sources (*reference basis: excluding combinations containing static-reg; not used in this report*) | 30,211 | 26.46% |

> 🔴 **Basis declaration**: this report uses the primary basis `≥2 sources = 30,259 / 26.50%` (including the 48 edges in which static-reg participates) throughout.
> - **Why**: the closure criterion `Σ layer-unique + ≥2-source edges = total edges` requires `83,916 + 30,259 = 114,175` ✅; with 30,211 the statement would have to be written `83,916 + 30,211 + 48 = 114,175`, adding a basis note and contradicting the combination distribution below.
> - 🚫 **Never mix the two values**: wherever "cross-confirmation rate" appears, it is **26.50%**.

**Source-combination distribution (full enumeration, closes)** `[measured]`:

| Combination | Edges | Note |
|:--|--:|:--|
| `static` only | 55,537 | — |
| `runtime + static` | **28,736** | **main intersection** |
| `runtime` only | 16,362 | static blind spot |
| `static-reg` only | 8,571 | registry-only |
| `asm` only | 3,446 | assembly-only |
| `asm + static` | 1,432 | asm functions called statically from C |
| `runtime + static-reg` | 46 | registration edge actually hit by runtime |
| `asm + runtime + static` | 42 | three-source confirmation |
| `static + static-reg` | 2 | — |
| `asm + runtime` | 1 | — |
| **Total** | **114,175** ✅ | |

### 2.4 "Why 26.50% is not high" — anti-misreading `[measured]`

26.50% invites misjudgement; here is its composition:

| Layer | Unique edges | Unique rate | Can it be cross-confirmed |
|:--|--:|--:|:--|
| static | 55,537 | 64.8% | can overlap with runtime |
| runtime | 16,362 | 36.2% | can overlap with static |
| **asm** | **3,446** | **70.0%** | ⚠️ `asm → asm` **cannot be confirmed by runtime** (no instrumentation point in assembly); but asm functions **can** be cross-confirmed by static (1,432 `asm+static` edges) |
| **static-reg** | **8,571** | **99.4%** | ❌ **different semantics** (possible vs actual); should not cross-confirm |

**⇒ The main cross-confirmation intersection is only `static ∩ runtime = 28,736` (95.0% of all ≥2-source combinations)**.

**Conclusion**: 26.50% reflects **how the layers' blind spots complement each other** — precisely because complementarity is strong (many unique edges), the cross-checkable part is naturally small. **A low number here does not mean poor quality; it measures "overlap between methods", not "trustworthiness of edges".**

### 2.5 static-reg's 99.4% uniqueness — why it is not a data error `[measured]`

| Source | Semantics | May overlap with |
|:--|:--|:--|
| **static-reg** | "**may be called**" (function-pointer table registration) | **semantically different** from runtime ("**actually called**") |
| **runtime** | "**actually called**" (trace record) | registered but never hit is not recorded by runtime |

**⇒ The relation is inclusion, not duplication**: something may be registered and never called; if it was called, there must be a registration or a statically visible path elsewhere. Static-reg edges therefore almost cannot be "confirmed" by other layers — **that is not a defect of this layer but a thing nobody else records.**

> 🚫 **When citing static-reg, the qualifier "may be called" is mandatory**; it must not be written as "actually called".

### 2.6 ID disambiguation (merge consistency) `[measured]`

> **Problem**: after multi-layer merging, same-named functions across files must be disambiguated, otherwise ghost nodes and wrong edges appear.

| Item | Value |
|:--|--:|
| Total edges | 114,175 |
| callee has `callee_id` | 98,756 |
| **Dangling callee** (`callee_id` not in graph) | **0** ✅ |
| caller has `caller_id` | 107,868 |
| **Dangling caller** | **0** ✅ |
| Mapping rate (callee, edge-level) | 0.8650 = 98,756 / 114,175 |
| **Closure check** | ✅ **True** |

**⇒ Zero dangling node IDs after merging** (cross-file disambiguation complete, no ghost nodes).

> **The table above is on-the-spot recomputation** (reading `edges[*].calls[*].caller_id / callee_id` directly). `summary.id_disambiguation` inside the graph is a snapshot from the same-name phase (based on 114,250 edges, before self-loop removal); its sub-items differ from this table, so **citations must state which one is used**.

**Three forms of `callee_id` (on-the-spot recomputation)** `[measured]`:

| Form | Edges | Nature |
|:--|--:|:--|
| **With `@` (disambiguated key)** | **88,343** | file uniquely determined, **0 dangling among them** ✅ |
| **Bare name (value present, no `@`)** | **10,413** | same name across files; the guard **refuses to guess** |
| **No value (`callee_id` null)** | **15,419** | **in-graph macro/inline helpers 2,802 + unmapped 12,617** |
| **Total** | **114,175** ✅ | |

**On the 15,419 "no callee_id" entries (do not mistake them for a defect)** `[measured]`:

Sampled verification splits these 15,419 into two classes: **2,802 point at in-graph macros / inline helpers** (they have a `file_map` entry but no node id, e.g. `av_bswap32` 1,212 edges, `av_bswap16` 605, `av_clip_uint8` 194); the other **12,617 are absent from `file_map`**, mostly external symbols. Typical samples of the latter:

| callee | Category |
|:--|:--|
| `__builtin_add_overflow` / `__builtin_clz` / `__builtin_sub_overflow` | compiler builtins |
| `abort` / `memcmp` | C standard library |
| `CloseHandle` / `CoUninitialize` | Win32 API |
| `IGraphBuilder_Release` / `IEnumFilters_Reset` | COM interface methods |

> Neither class **has a function node to point at**: external symbols have no source ownership, while macros / inline helpers leave no standalone definition after expansion. **Leaving them empty or bare is correct behaviour, not missing data**.
>
> **Design trade-off**: we would rather leave them empty or bare than **complete them by guessing** — any "guessed identity" pollutes every downstream statistic and is not auditable.

### 2.7 Conclusion of this chapter

| Dimension | Conclusion |
|:--|:--|
| **Coverage gain** | merged 114,175 vs edges containing static 85,749 (static-primary 55,539) → **+33.1%** |
| **Irreplaceability** | runtime + asm + static-reg three **paths** contribute **28,379 unique edges** in total (no single layer alone can obtain them) |
| **Confidence** | **26.50%** (30,259 pairs) of edges are cross-confirmed by **≥2 independent methods** |
| **Consistency** | after merging, dangling IDs **0**; closure checks pass |

**⇒ Core conclusion: a single-layer approach (pure static / pure dynamic / pure registry) cannot obtain "coverage breadth + cross-source confidence + dynamic completion" at the same time.** This is not the linear addition of "one more source, a bit more edges", but **three paths each covering the others' structural blind spots** — runtime fills the indirect calls static cannot see, asm fills the assembly calls C parsing cannot see, static-reg fills the registration relations neither of them can see.

**⇒ The converse also holds**: precisely because the three paths complement each other, **the unique edges (83,916 / 73.50%) are single-source by definition and cannot be cross-confirmed**. So "26.50% cross-confirmation rate" and "73.50% unique edges" are two sides of one fact — **it is not "quality of only 26%"**.

---

## 3. Construction mechanism (five layers plus one frozen layer)

### 3.1 Layer A · Macro expansion `[measured]`

| Item | Value |
|:--|--:|
| Files expanded successfully | **2,257 / 2,257** (0 degraded) |
| Line-mapping sites | **258,791** (0 unmapped) |
| Deduplicated contributed edges | **18,745** |
| Files with mappings | 2,208 |

**Role**: macro expansion changes line numbers and call shapes. Layer A builds a "preprocessed line ↔ original source line" mapping so that Layer B's call-site line numbers return to the source lines the user sees.

> ⚠️ **Layer A is not counted separately in `source` edge counts**: the edges Layer A produces are filed under `static` (Layer B). Its 18,745 is an **exclusive contribution**, and a **subset** of Layer B's unique 55,537, so it is not added again.
>
> ⚠️ `mapped_sites 258,791` is the **line mapping of macro expansion**, **not** line-coverage data — this tool produces no line execution state.

**Layer A physically unsolvable items = 0** (not "we skipped it" but "this class does not exist"):

> **Reason**: the C preprocessor is **not Turing-complete** (`#define` does not support recursion) → macro expansion is necessarily **finite-depth** → `gcc -E` can process every translation unit. **Real undecidability happens after expansion** (function pointers / dynamic dispatch), which is a boundary of Layers B / D, not of Layer A.
>
> Hence `expand_succeeded 2,257 / 2,257` and `unmapped_sites 0` are not luck but **structural necessity**.

### 3.2 Layer B · Static parsing `[measured]`

| Item | Value | Data source |
|:--|--:|:--|
| Files scanned | **2,257** | `meta.total_files` |
| Function definitions parsed | **31,500** | `meta.total_functions` |
| static edges (primary) | **55,539** | `meta.edge_source_breakdown.static` |
| Resolved edges | 44,292 | `meta.resolved_edges` |
| Unresolved edges | 11,247 | `meta.unresolved_edges` (**edge count, not symbol count**; includes external symbols) |
| Resolution rate (edge-level) | 0.7975 | `meta.resolved_edge_ratio` |
| Parse coverage | **1.0** | `summary.parse_coverage` |
| **Truly unresolved inside project** | **0** | `summary.true_project_unresolved` |
| **Edges carrying source call sites** | **79,873** | `summary.static_edges_with_call_sites` |
| call_coverage | 0.9315 | `summary.call_coverage` |

**Noise filtering** `[measured]`: **20,879** edges filtered (15.45%), **overkill = 0**; node-level filtering 4,239.

| Filter category | Count |
|:--|--:|
| `macro_name` | 13,144 |
| `template_instantiation` | 7,252 |
| `short_name_noise` | 476 |
| `c_keyword` | 6 |
| `c_type_name` | 1 |

> Basis note: `filtered_by_kind` totals 21,588, which differs from the effective 20,879 by **709** = `alias_targets_found` (that item is a "found" counter, not a "filtered" counter).
>
> **Definition of overkill = 0**: **not one** filtered edge finds corresponding evidence in the runtime trace or the assembly layer. This is the most important quality indicator of this layer.

**Node-level filtering** `[measured]`:

| Category | Nodes |
|:--|--:|
| `macro_name` | 4,236 |
| `c_keyword` | 2 |
| `c_type_name` | 1 |
| **Total** | **4,239** (= `summary.filtered_nodes_total`) |

**🔴 Post-mortem of one "tool false alarm" (methodology, worth publishing)** `[measured]`:

An internal quality tool once reported "**25,245** suspicious residues" — accepting that would have led to "filtering is badly insufficient". The actual investigation:

| Step | Result |
|:--|:--|
| Tool-reported suspicious residues | 25,245 |
| Manual sampling | **9 / 9 all genuine function nodes** (e.g. `av_assert0@ffmpeg-src#libavutil#avassert.h`) |
| Root cause | The tool's `dotted` predicate matched a dot on the **entire key**, and the dot came from the **file name** (`avassert.h`), not from a legal identifier |
| Conclusion | **Filtering had no overkill; the audit tool's predicate was flawed** |

> **Why this is worth writing down**: it shows that "problems reported by audit tools" themselves need auditing. We did not "fix" a filter that was already correct because of those 25,245 — **doing so would have deleted real functions**.

**Layer B physically unsolvable items = 1 class**:

> **Reason**: the call target of **function pointers / dynamic dispatch** is undecidable at compile time (a corollary of Rice's theorem). Other "unresolved" cases (e.g. external library symbols, **11,247** edges) are an **engineering boundary** — they have no source, they are not undecidable.
>
> **Truly unresolved inside project = 0** (`summary.true_project_unresolved`) → **the static part is complete**. That is the precise meaning of "done": not "all edges resolved", but "**every edge that has source to resolve has been resolved**".

### 3.3 Layer D · Runtime instrumentation `[measured]`

| Item | Value |
|:--|--:|
| FATE cases | **9,033** |
| runtime edges (`summary.edge_source_breakdown.runtime`) | **45,187** |
| Of which also carry asm evidence (not counted again) | **43** |
| Unique runtime addresses | **85,754** (callee 23,622 / call_site 62,132) |
| Address resolution success rate | **100%** (85,754 / 85,754) |
| Resolution self-check (resolved name vs bare name recorded by trace) | **100%** (49,631 / 49,631) |
| Resolution time | 6 seconds |
| Total function entries | **666,777,159,159** (≈666.8 billion) |
| Data status | `meta.runtime.status = reused` (reuses an existing trace; rebuilding the graph does not change runtime behaviour) |

**🔴 Two different "address resolution" figures (must read, avoid confusion)**:

This layer has two different "address resolution success rates" whose values differ hugely and **do not contradict**:

| Basis | Value | Meaning | Who did it |
|:--|--:|:--|:--|
| **① trace-internal address pairing** | success **257,443** / unresolved **1,069,925** (**79.8% unresolved**) | pair "call-site address → function entry address" inside the trace; on failure **no edge is produced** for that entry | Layer D data collection (Frida + symbol table) |
| **② DWARF resolution in §3.3 here** | success **85,754 / 85,754 = 100%** | translate the **already paired** unique addresses into `file::func` + source line | new in this version (offline `addr2line`) |

> **① is "can they be paired"; ② is "once paired, can they be translated"**. Failure in ① means **edges may be missing** (no edge for that entry); success in ② only shows the translation step loses nothing.
>
> **Resulting limitation**: the **1,069,925** unresolved address entries **were not included in the edge statistics**, so `runtime 45,187` is **a lower bound, not the full set**. The causes for these unresolved entries (cross-module calls / dynamic loading / no symbols) **have not been classified one by one** — listed in §6 #12.

**Collection method**: Frida hooks function entries and records `callee_addr` (called function address), `call_site_addr` (address where the call happened) and the call count.

**Address resolution (key improvement in this version)**:

> **Problem**: the trace records only **bare function names**, and the same name may be defined in many files — e.g. `filter_frame` exists in **265 files** under libavfilter (one per filter, all `static`).
> **Consequence**: matching bare names against an identity-based denominator gives a function 1 numerator but occupies 263 denominators — **the rate is systematically depressed**.
> **Approach**: use the binary's DWARF (`.debug_line` / `.debug_info`) to resolve addresses offline into `file::func` + source line. **No recompilation, no re-running of tests** (85,754 addresses, 6 seconds).
> **Self-check**: the resolved function names and the bare names recorded by the trace agree **49,631 / 49,631 = 100%** — proving the addresses and the symbol table come from the same build, with no version drift.

**By-product**: resolution simultaneously upgrades runtime edges to identity granularity, making **edge-by-edge reconciliation between static and runtime edges measurable for the first time** (see §5.1).

### 3.4 Assembly layer `[measured]`

| Item | Value |
|:--|--:|
| Assembly functions identified | **7,420** |
| Assembly call sites | **3,980** |
| Source side / Capstone side | 1,347 / 5,689 (384 in both) |
| **asm edges in graph** | **4,878** |
| Registration nodes | 4,652 |
| Self-reported three-value agreement | `meta.asm_layer.merged_edges` = `summary.asm_layer.merged_edges` = per-edge `source=asm` = **4,878** ✅ |

> ⚠️ **Do not confuse the fields**: in the same object, `asm_layer.edges` = **3,980** (call sites on the source side) and `asm_layer.merged_edges` = **4,878** (edges in graph). They are not synonyms; citations must name the field.

**🔴 Closing the 898 difference between `asm_calls` 3,980 and `merged_edges` 4,878** `[measured]`:

| Item | Value | Meaning |
|:--|--:|:--|
| `asm_calls` | **3,980** | call relations obtained by **source parsing** (`call`/`bl`/`jmp` in `.asm`/`.S` text) |
| asm edges in graph, split by `asm_origin` | | |
| ├ `capstone` | 3,695 | Capstone disassembly only |
| ├ `source` | 154 | source parsing only |
| ├ `both` | 88 | hit by both paths |
| └ `None` (no origin tag) | 941 | registration / other paths |
| **Total** | **4,878** | = `merged_edges` ✅ |

> **Where the 898 comes from**: the two numbers **have different sources**. Edges in graph are dominated by Capstone disassembly (3,695 + 88 = 3,783); source parsing contributes only 154 + 88 = 242 in-graph edges, plus 941 without origin tag. `asm_calls` counts only call instructions in source text and **does not include** edges discovered by disassembly. 🚫 **Never subtract the two and call the result "missing edges"**.

**Precise meaning of "done" for the assembly layer** `[measured]`:

| Indicator | Value | Meaning |
|:--|--:|:--|
| `asm_functions` | **7,420** | all assembly functions in graph |
| `asm_calls` | **3,980** | assembly call relations resolved (source side) |
| `both` (source + Capstone) | 384 | dual-path cross-validation |
| `merged_edges` | **4,878** | assembly edges in graph after merging |
| **asm-form nodes in graph** | **4,813** | exact key form (`.asm` / `.S`) |
| **Residue: assembly macro arguments** | **x86 86 + aarch64 226** | ⏸️ call targets passed as macro arguments, **current methods exhausted** |

| Statement | Accurate? |
|:--|:--|
| "The assembly layer is fully resolved" | ❌ inaccurate |
| "The assembly layer's **reachable call edges** are all in the graph" | ✅ accurate |

> Assembly contains many constructs with **no instrumentation point and no source visibility** (indirect jump tables, trampolines, hand-written SIMD dispatch). "Done" for this layer means **edges confirmable from both source and disassembly are all in the graph**, not that "every possible control flow in assembly has been recovered".
>
> **Explicit residue**: call targets passed as **macro arguments** remain unresolved at **86** sites on x86 and **226** on aarch64. This is the only known, counted residue of this layer (see §6).

### 3.5 Registry (static-reg) `[measured]`

| Item | Value |
|:--|--:|
| Files scanned | **2,257** |
| Patterns identified | **32,823** |
| Members | 9,923 |
| **Registration edges (resolved)** | **9,625** |
| ├ asm callees | 988 |
| └ C callees | 8,637 |
| **static-reg edges in graph (`source`)** | **8,571** |
| static-reg edges in graph (`sources` contains) | 8,619 |
| **Resolved → in-graph difference** | **1,054** |

Closure check: `988 + 8,637 = 9,625` ✅

**🔴 Closing the 1,054 entries from 9,625 → 8,571** `[measured]`:

| Segment | Explanation | Count |
|:--|:--|--:|
| ① Edges resolved from the registry | caller = table name, callee = member function (**including callees not in graph**) | 9,625 |
| ② In graph (`source=static-reg`) | callee must be in graph and not overridden by a higher-priority source | **8,571** |
| ③ Overridden by a higher-priority source (`sources` contains static-reg but `source` is not static-reg) | e.g. `runtime+static-reg` 46 / `static+static-reg` 2 | 48 |
| ④ **Not in graph** (callee not in graph / filtered as noise) | ① − ② − ③ | **1,006** |

> 🚫 **Never treat 9,625 and 8,571 as contradictory** — the former is "resolved", the latter "successfully in graph".

**Semantics**: registry edges = "**may be called**" (function-pointer-table members), **not "actually called"**. Independent citation must carry this qualifier (see §2.5).

### 3.6 Layer C · LLM inference (**disabled**) `[measured]`

| Item | Value |
|:--|--:|
| Candidate points | probed |
| Edges produced | **0** |
| Status | **frozen (disabled)** |

**Basis for freezing (quantitative, not "felt useless")** `[measured]`:

| Item | Value | Comparison baseline |
|:--|--:|:--|
| **Layer C candidate gap** | **92** call sites | **3.37%** of the **2,727 member-function-pointer call sites** |
| **Actually fillable after removing false alarms** | **36** call sites | **1.32%** of 2,727 |
| Of which removed: AAC 56 sites | 55 macro-name false alarms + 1 internal static function | **does not constitute fillable surface** |
| Composition of the 36 fillable sites | Vulkan 24 + ffplay 5 + others 7 | of which **29 are platform-specific code** (`#ifdef`) |
| **Already covered by `static-reg`** | **8,571** edges | = **93×** the 92 candidates / **238×** the 36 actually fillable |
| **Layer C historical close rate** | **5 / 14,668 = 0.03%** | threshold: freeze when solve rate < 1% |

**⇒ Conclusion: Layer C's potential gain (36 call sites) is already covered by `static-reg` (8,571 edges) at 238× the scale and near-zero cost.** The marginal gain of LLM inference is far below the unverifiable risk it introduces.

**📌 When it is worth using (exception scenario, important)**:

| Scenario | Is Layer C worth enabling |
|:--|:--|
| FFmpeg itself (this report's subject) | ❌ **Not worth it** — the registry already covers it |
| Libraries heavy on `dlopen` / plugin architectures | ✅ **Possibly worth it** — their call targets have neither a stable static registry nor stable runtime coverage |

> **This matters more than "we froze Layer C"**: it shows the freeze is a **judgement about FFmpeg**, not the general conclusion "LLM inference is useless". **Change the architecture and the conclusion may reverse.**

**⇒ This version actively disables it, rather than "has not got round to it".**

**Design trade-off**: rather forgo stacked inference than introduce unverifiable edges. The reason is that this tool's positioning is an **auditable relation graph** — an edge that "looks plausible but cannot be verified" pollutes every downstream statistic built on it (especially `target_set` and the confidence tiers).

> 🚫 **Never phrase it as "the LLM layer is not implemented yet"** — it is **implemented, validated and deliberately switched off**.
> 🚫 **Never phrase `llm: 0` as a defect** — `meta.llm.status = disabled`; this is a **design state**.

### 3.7 Declaration of source-field bases (important) `[measured]`

> ⚠️ The graph has **two source fields** with different bases, and **citations must say which**:

| Field | Meaning | Value |
|:--|:--|:--|
| `source` (single value) | **primary source** (exactly one per edge) | `static` 55,539 / `runtime-confirmed` 45,187 / `static-reg` 8,571 / `asm` 4,878 / `llm` 0 (**total 114,175**) |
| `sources` (array) | **all sources** (overlapping, may be several) | `static` 85,749 / `runtime` 45,187 / `static-reg` 8,619 / `asm` 4,921 (**not additive**) |

**⇒ `meta.edge_source_breakdown` uses the `source` basis; the multi-source cross analysis in §2 uses the `sources` basis. 🚫 Never mix the two.**

> Why they differ: an edge may be found by static and runtime at once. `source` records only the **highest-priority** one (hence the total is exactly 114,175); `sources` records **all layers that found it** (hence static totals 85,749 > its primary count 55,539).

---

## 4. Data specification

### 4.1 Graph file structure

```
acd_graph.json
├── workspace_root   source root path
├── generated_at     creation time
├── summary          self-reported statistics (parse_coverage / filtered_* / asm_layer etc.)
├── meta             per-stage metadata (a_layer / asm_layer / gap_class / self_loop …)
├── file_map         function name → declaring file (39,553 entries; **single-value table, multiple definitions of one name get flattened**)
└── edges            node → { calls: { callee node: edge metadata } }
```

**Node key format**: `<func>@<src>#<path>#<file>`
Example: `av_fifo_can_write@ffmpeg-src#libavutil#fifo.c`

> **The key itself carries the full file path** and is the authoritative source of identity; `file_map` is only a bare-name index (lossy, see §6 #6).

**Edge metadata fields**:

| Field | Meaning |
|:--|:--|
| `sources` | which layers confirmed the edge (static / runtime / asm / static-reg) |
| `source` | primary source (single value, used for layer statistics) |
| `call_sites` | source call sites `file:line` (**present on only ~70% of edges**) |
| `trace_count` | runtime call count |
| `callee_addr` / `call_site_addr` | runtime addresses (resolvable to `file:func` / `file:line`) |
| `callee_id` / `caller_id` | disambiguated node ids (forms in §2.6) |
| `confidence` | confidence label |

### 4.2 Edge-count closure chain (recomputable segment by segment) `[measured]`

| Segment | Computation | Value | Data source |
|:--|:--|--:|:--|
| ① Before filtering | — | 135,129 | `summary.edges_before_filter` |
| ② Noise filtering | ① − 20,879 | 114,250 | `summary.edges_actual` ✅ |
| ③ Post-process edge removal (out-edges of removed nodes) | ② − 64 | 114,186 | `meta.self_loop.edges_before` |
| ④ Self-loop `FALSE_POSITIVE` removal | ③ − 11 | **114,175** | `summary.total_edges` ✅ |

> **Honest note on the 64 entries in segment ③**: that segment comes from the post-processing stage (removing short-name nodes `c` / `s` etc. along with their out-edges), and **currently no `postprocess_edge_dropped` counter field is written**, so only the two ends ②→④ can be verified; **segment ③ is not recomputable edge by edge**. The fix is identified (add that counter in `build_acd.py`'s post-processing stage) but not implemented in this version.

### 4.3 Identity and denominator definitions `[measured]`

| Basis | Definition | Value |
|:--|:--|--:|
| Nodes in graph | `edges.keys()` (caller side) | **38,697** |
| key ∪ callee (incl. external symbols) | widest graph-theoretic basis | **40,167** |
| Nodes with `file_map` | including bare-name fallback | **36,099** |
| Nodes without `file_map` | registration symbols / macro products / assembly | **2,598** |
| **Instrumentable denominator `instrumentable`** | has `file_map` and non-assembly (identity-deduplicated) | **31,305** |
| `real_denom` | `instrumentable − macro 95 − unused 7 − ffprobe 95` | **31,108** |

**Denominator correction terms** `[measured]`:

| Term | Count | Explanation |
|:--|--:|:--|
| `macro` | 95 | macro names misidentified as functions |
| `unused` | 7 | code paths not enabled |
| `ffprobe` | 95 | ffprobe-only (outside this graph's scope) |
| **Total** | **197** | **the three do not overlap → net removal 197** |

Closure check: `31,305 − 197 = 31,108` = `real_denom` ✅

> 🚫 **Never call 40,167 "the total number of FFmpeg functions"** — it includes external symbols (Win32 API / compiler builtins). The denominator is always `instrumentable` (31,305).
>
> `40,167 − 38,697 = 1,470` = "bare-name callees with no corresponding node in graph".
>
> `31,500` (parsed function count) and `31,305` (after identity dedup) differ by **195**, caused by assembly functions without `.c` definitions, macro-argument placeholders, etc. That difference is an **internal data-maintenance matter** and does not affect the denominator definitions above.

### 4.4 Denominator cross-checks `[measured]`

| Check | Result |
|:--|:--:|
| `total = with_fm + no_fm` | ✅ 38,697 = 36,099 + 2,598 |
| `total = no_in + has_in` | ✅ 38,697 = 13,430 + 25,267 |
| `instrumentable ≤ with_fm` | ✅ 31,305 ≤ 36,099 |
| `noin_instrumentable ≤ without_inbound` | ✅ 7,239 ≤ 13,430 |
| `nt = no_inbound_non_simd + with_inbound_in_nt + SIMD` | ✅ 15,598 = 6,232 + 8,143 + 1,223 |

**Graph binding**: `graph_md5 = b357bf8e…` (on-disk / release anchor) ✅ ｜ `denominator.json` md5 **`1da5867b…`** (distribution copy 1,955 B; audit original `616cb5e3…` same values)

**🔴 `with_inbound_all` 25,267 vs `gap_class.HAS_INBOUND` 25,420 — difference 153 (basis difference, not an error)** `[measured]`:

| Basis | Definition | Value |
|:--|:--|--:|
| `denominator.with_inbound_all` | after normalisation by `_ident()` (bare name + primary file), identities with inbound edges | **25,267** |
| `gap_class.HAS_INBOUND` | counted by **node key**, nodes with inbound edges | **25,420** |
| **Difference** | | **153** |

**Closure (measured)**:
- key has inbound but `_ident` has none (`_ident` returns `None` = no `file_map`) = **154** nodes (e.g. `av_frame_side_data_get` / `ff_dshow_*_AddRef`)
- `_ident` has inbound but key has none = **1** node (`refill`)
- **154 − 1 = 153** ✅ closes

> 🚫 **Never compare or subtract 25,267 and 25,420 as an error** — the bases differ (identity-normalised vs node key).
>
> **The no-inbound side has a symmetric 153 difference** (the other face of the same basis difference): `denominator.without_inbound` **13,430** (identity basis) vs the `gap_class` no-inbound five-class total **13,277** (node-key basis). Closure: `13,277 + 25,420 = 38,697` ✅ ｜ `13,430 + 25,267 = 38,697` ✅

**🔴 `nt` is a set difference, not a numeric difference (must read, to avoid "subtracting and getting 61 off")** `[measured]`:

`nt` (untouched) = `real_denom − touched` is **a difference of two identity sets**, not the subtraction of two numbers:

| Method | Result |
|:--|--:|
| Approximate: `real_denom − touched` = `31,108 − 15,571` | 15,537 |
| **Actual `nt`** | **15,598** |
| Difference | **61** |

**Where the 61 comes from (measured, explainable)**:

> `touched ∩ (macro ∪ unused ∪ ffprobe) = 61` — these 61 functions **were executed (inside `touched`) but have been removed from the denominator (inside macro / unused / ffprobe)**.
>
> Exact formula: `|real_denom − touched| = |real_denom| − |touched| + |touched ∩ (macro∪unused∪ffprobe)| = 15,537 + 61 = 15,598` ✅

> 🚫 **Never subtract numerically** (that yields 15,537, off by 61, i.e. 0.39%). This is the trap in this report most easily hit by "manual cross-checking", hence its own paragraph.

### 4.5 gap_class: five-way typing of no-inbound nodes `[measured]`

| Class | Definition | Nodes |
|:--|:--|--:|
| `HAS_INBOUND` | has inbound edge (static / runtime / asm / reg, any) | **25,420** |
| `UNKNOWN_ASM` | no inbound + assembly path or bare name hitting the assembly map | **4,572** |
| `UNKNOWN_DYNAMIC` | no inbound + dynamic-call candidate | **3,611** |
| `DEAD_SUSPECT` | no inbound + suspected dead code | **2,650** |
| `NO_FILE_MAP` | no inbound + no `file_map` | **2,444** |
| **Total** | | **38,697** ✅ |

Closure: `13,277 + 25,420 = 38,697` (13,277 = sum of the last four) ✅

> The last four classes are **"a typing of no-inbound nodes"**, not "conclusions about function quality". `DEAD_SUSPECT` merely means "no inbound edge found in the current graph and the features match dead code"; **it does not confirm dead code** — it too is a candidate pool for supplementary testing / review.

---

## 5. Quality evidence

### 5.1 Edge-level reconciliation (recomputed edge by edge on the bound graph, per `docs/caliber.md` §2.12) `[measured]`

**Basis** (static-family edges = `sources` contains `static` or `static-reg` and not `asm`; runtime edges = `summary.edge_source_breakdown.runtime`; matched = intersection of the two at **identity (`file::func`) granularity**):

| Item | Edges | Note |
|:--|--:|:--|
| Static-family edges (static ∪ static-reg, non-asm) | 92,892 | recomputed per-edge `sources` |
| Runtime edges | **45,187** | `docs/caliber.md` §2.12 |
| **Matched (both sides)** | **28,782** | **= 63.7% of runtime edges** |
| Runtime only | 16,405 | not captured by static (incl. cross-module / shared libraries) |
| Static only | 64,110 | not covered by runtime, or registered but never actually called |
| Closure checks | `28,782 + 16,405 = 45,187` ✅ ／ `28,782 + 64,110 = 92,892` ✅ | — |

> **How to read it**: 63.7% of runtime edges can be independently confirmed by static parsing, showing **static recall is reliable** — it does not massively "miss calls that actually happen".
>
> ⚠️ **63.7% is a matched rate, not precision**; basis in `docs/caliber.md` §2.12 `matched_rate`, recomputation script `scripts/verify_matched_rate.py`.
>
> 🔴 **The set from the v4.0 first draft is void** (static 78,425 / runtime 45,198 / matched 35,562 = 78.7% / runtime only 9,636 / static only 42,863). Among them `45,198` came from a stale table already marked "do not cite" (bound to `8722fe68`, 110,985 edges); `78,425 / 35,562 / 9,636 / 42,863` cannot be reproduced on the currently bound graph (`b357bf8e`, 114,175 edges) under any of identity / name-level / all-bare-name joins (the three bases give 63.7%, 63.7%, 68.4% respectively).
>
> `Static only 64,110` **does not mean static is wrong** — it mixes "registered but never called" and "not covered by tests", **not yet classified one by one** (see §6 #2). This number is currently the largest single black box.

### 5.2 Noise-filter distribution `[measured]`

| Item | Value |
|:--|--:|
| Edges before edge-level filtering | 135,129 (`summary.edges_before_filter`) |
| Edge-level filtered out | **20,879** (15.45%, `summary.filtered_edges`) |
| **Overkill** | **0** ✅ |
| Node-level filtered | 4,239 (`summary.filtered_nodes_total`) |
| Edges after filtering | 114,250 (`summary.edges_actual`) |

> 114,250 differs from the total 114,175 by **75** = 64 post-process edge removals (§4.2 ③) + 11 self-loop false positives (§4.2 ④); the 64 have no separately recorded counter, so only the two ends close — flagged as not individually recomputable in §4.2.

**How overkill = 0 was determined** `[measured]`: for every filtered edge, check the runtime trace and the assembly layer for corresponding evidence — **evidence found counts as overkill**. Measured 0, i.e. every removed "noise" edge truly leaves no trace in any layer.

**Main noise categories**: `macro_name` 13,144 (macro names misread as calls) / `template_instantiation` 7,252 (template instantiation products) / `short_name_noise` 476 (over-short function names) / `c_keyword` 6 / `c_type_name` 1.

> Basis note: `filtered_by_kind` totals 21,588, differing from the effective 20,879 by **709** = `alias_targets_found` (a "found" counter, not a "filtered" counter).

> **Residue not fully removed (separate account, not in the table above)**: `overkill=0` proves only "nothing correct was deleted", not "everything was deleted". Three kinds of residue remain in the filtered graph; none changes the caliber and none is subtracted from 114,175:
> - **The filter itself reports 42 items**: the engine's `debug_filter_audit` reports 42 keys still matching the lower_macro_like / dotted criterion (not individually classified; e.g. `NEG_USR32` appears at 36 callers). That tool's dotted criterion once produced 25,245 whole-key false positives (§3.2), so these 42 need individual review before they can be characterized.
> - **232 edges whose callee is a syntax keyword / compile-time builtin**: `__typeof__` (159), `__builtin_offsetof` (38), `_Static_assert` (20), `static_assert` (14), `__attribute__` (1).
> - **8 edges whose callee is an assembly local label**: `$fcc0` (LoongArch assembly local label).

### 5.3 Self-loop detection and repair `[measured]`

| Item | Before | After | Change |
|:--|--:|--:|--:|
| `total_loops` (classified total, before removal) | 1,341 | **85** | −1,256 |
| `FALSE_POSITIVE` | 1,261 | **11** | **−1,250** |
| `UNKNOWN_NO_SRC` | 2 | **0** | −2 |
| `TRUE_RECURSION` | 72 | **72** | 0 |
| `ADDR_ONLY` | 1 | **1** | 0 |
| `ASM_NO_JUMP` | 1 | **1** | 0 |
| `Others` (unclassified residue) | 4 | **0** | −4 |
| `removed` | 1,261 | **11** | **−1,250** |
| `bare_removed` (bare-name false removal) | — | **0** ✅ | — |

**Closure checks**: `1,341 = 1,261(FP) + 2(UNKNOWN) + 72(TRUE) + 1(ADDR) + 1(ASM) + 4(others)` ✅
**Change closure**: `−1,256 = −1,250(FP) − 2(UNKNOWN) + 0 + 0 + 0 − 4(others)` ✅
**Current state**: classified total **85** (including 11 false positives, already removed); the graph actually retains **74 genuine self-loops** (`TRUE_RECURSION` 72 + `ADDR_ONLY` 1 + `ASM_NO_JUMP` 1).

**Root causes (line-level, reproducible)** `[measured]`:

| Defect | Root cause | Fix |
|:--|:--|:--|
| **1,261 bare-name self-loops falsely removed** | for bare-name keys (no `@`) → `rel=""` → `src_path=""` → unconditionally judged `FALSE_POSITIVE` and the edge deleted | bare name → single-value reverse lookup in `file_map`; if unresolvable → new class `UNKNOWN_NO_SRC`, **not deleted** |
| **`_enclosing_func_by_scan` has no brace matching** (the real root cause of the 1,261 false loops) | only "scan upwards for the nearest function header + next non-empty line is `{`", **without verifying the target line is inside the function body** → file-level `static const AVFilterPad xxx[]` was misattributed to the preceding function | add a "upper bound = closing `}` of the function" check |

**Root-cause evidence** (`libavfilter/aeval.c`):

```
L410  static int filter_frame(AVFilterLink *inlink, AVFrame *in)   → function header
...
L445  }                                                             → end of function
L447  #if CONFIG_AEVAL_FILTER
L449  static const AVFilterPad aeval_inputs[] = {                    → file-level, outside the function
L453      .filter_frame   = filter_frame,
L455  };
```

Before: `_enclosing_func_by_scan(aeval.c, 453)` → **`'filter_frame'`** (wrong, L453 is outside the function)
After: → **`''`** (correct)

> **Causal chain**: `enc='filter_frame'` → when extracting registration edges `caller = enc or table` → caller changed from the table name `aeval_inputs` to the function name `filter_frame`, while the registered member name was also `filter_frame` → a fake self-loop `filter_frame → filter_frame` → judged `FALSE_POSITIVE` and removed → **both a fake edge was deleted and a real registration edge was lost**.

### 5.4 Criteria system (two tiers, each item labelled with verifiable strength)

This tool has a **two-tier** criteria system: **s200 (in-graph self-consistency, 16 items)** + **C1–C8/D1b (report internal consistency, 9 items)**. Both tiers **label verifiable strength item by item**, and do not treat "run PASS" as "data all correct".

#### Tier 1 | s200 · in-graph self-consistency, 16 items `[measured]`

| # | Criterion | Expected | Measured |
|:--:|:--|:--|--:|
| 1 | non-static-reg `reg_table` non-empty | 941±5 | **941** |
| 2 | `reg_table` not a callee-name prefix | 0 | **0** |
| 3 | static-reg `reg_table` non-empty | 7,884 | **7,884** |
| 4 | static-reg `reg_table` not a variable name | 0 | **0** |
| 5 | `self_loop_class` coverage | 85 | **85** |
| 6 | `TRUE_RECURSION` | 72 | **72** |
| 7 | `FALSE_POSITIVE` removed | 11 | **11** |
| 8 | `ADDR_ONLY` | 1 | **1** |
| 9 | `ASM_NO_JUMP` | 1 | **1** |
| 10 | `asm_layer.merged_edges` == per-edge asm | equal | **4,878 = 4,878** |
| 11 | `HAS_INBOUND` without `file_map` must be tagged `no_file_map` | all tagged | **154 / 154** |
| 12 | `coverage_stale / last_full` == meta | equal | **equal** |
| 13 | `parse_coverage` must-fail unit tests | all PASS | **F-1/F-2/F-3 PASS** |
| 14 | Edge count | 114,175 | **114,175** |
| 15 | Node count | 38,697 | **38,697** |
| 16 | `gap_class` five classes | 25,420/2,650/3,611/2,444/4,572 | **all equal** |

**Result: 16 / 16 PASS.**

**🔴 But what matters more is proving "the criteria can fail"** `[measured]`:

> Point the same criteria at the **old graph** (`3e6b95ae…`, the on-disk graph before this rebuild) → **14 / 16 FAIL**.
>
> **This matters more than the 16/16 PASS**: it proves the criteria are **not tautological**. A criteria set that always passes is no criteria at all. **Negative-case validation is the credibility foundation of this tool's criteria system.**

#### Tier 2 | C1–C8 / D1b · report internal consistency, 9 items `[measured]`

> Tier 1 validates only **in-graph self-consistency**, not **report internal consistency** (whether the report computes correctly or contradicts itself). Tier 2 addresses exactly that.

| Criterion | Content | Status | **Verifiable strength (stated honestly)** |
|:--:|:--|:--:|:--|
| **C3** | runtime closure: edges in graph containing runtime = `edge_source_breakdown.runtime` | PASS | ✅ **true recomputation** — the left side is **re-walked edge by edge** from the graph and can fail independently |
| C2 | `nt` three-way split: 6,232 + 8,143 + 1,223 = 15,598 | PASS | ⚠️ **same-source arithmetic** — four values from one source; validates arithmetic only, **not the correctness of the classification** |
| C5 | `with_inbound` two bases: 25,420 − 25,267 = 154 − 1 = 153 | PASS | ⚠️ **partly measured** — 154 measured this round, `1` not archived |
| **C4** | unique-edge closure: 83,916 + 30,259 = 114,175 | PASS | ⚠️ **structural identity** — every edge is either "exactly 1 source" or "≥2 sources"; **mathematically impossible to FAIL** |
| **C7** | edge-count four segments: 135,129 − 20,879 − 64 − 11 = 114,175 | **TAUTOLOGY** | ❌ **tautological** — `before_filter` was never written to disk → `before` is back-derived and then subtracted back; **not a validation** |
| **C1** | `nt` set difference: 15,537 + 61 = 15,598 | PASS | ✅ **true recomputation** — the exclusion lists are on disk (§6.2.3); measured `touched ∩ macro = 61` (all macro), no longer relying on back-derivation |
| **C6** | register closure: 9,625 = 8,571 + 48 + 1,006 | PASS | ❌ **depends on unarchived data** — 48 / 1,006 not on disk; substituted by the `asm_callees + c_callees` split check |
| **C8** | member function pointers three-way: 958 kinds / 2,727 sites | **NOT_RECOMPUTABLE** | ❌ **not recomputable** — neither 958 nor 2,727 has an on-disk artifact |
| **D1b** | denom chain: 31,305 − 95 − 7 − 95 = 31,108 | PASS | ✅ **true recomputation** — the 95/7/95 lists are on disk and checkable entry by entry (§6.2.3); all 11 denominator-chain fields recompute consistently under this repo's definitions (`docs/caliber.md`) (§6.2.2) |

**Statistics: PASS 7 ／ TAUTOLOGY 1 ／ NOT_RECOMPUTABLE 1 (9 total).**

**🔴 But the 7 PASS must not be read as "7 items verified"**:

| Real verifiable strength | Count | Criteria |
|:--|--:|:--|
| **True recomputation (can fail independently)** | **3** | C1 / C3 / D1b |
| Structural identity (cannot FAIL mathematically) | 2 | C4 / C7 |
| Same-source arithmetic (arithmetic self-consistency only) | 2 | C2 / C5 |
| **Depends on unarchived artifacts (not independently recomputable)** | **2** | C6 (register's 48 / 1,006) / C8 (958 / 2,727) |

> **Improvement in this version**: the three exclusion lists (`macro` / `unused` / `ffprobe`) are now **on disk** (§6.2.3), and all 11 denominator-chain fields recompute consistently under this repo's definitions → **C1 and D1b upgraded from "depends on unarchived" to "true recomputation"**, raising the true-recomputation count from 1 to **3**.
>
> **Only 2 remain non-recomputable**: C6 depends on the register 48 / 1,006 detail, C8 on the member-function-pointer probe artifacts (958 kinds / 2,727 sites). Both are in the completion path of §6.2.5.

#### Side conclusion | True dead code = 0 `[measured]`

> After attributing **no-inbound** nodes class by class, **residual true dead code = 0**.
>
> That is: the **2,650** `DEAD_SUSPECT` nodes are not "confirmed dead code", but "no inbound found in the current graph and features match" — after attribution all of them fall into explainable classes such as assembly path / dynamic candidate / no `file_map`. **This is why this tool stays restrained about the term "dead code".**

---

## 6. Boundaries and limitations (**full disclosure**)

| # | Limitation | Nature |
|:--:|:--|:--|
| 1 | **Edge precision unverified by sampling**: this tool proves "the edge exists" (there is a call site / a trace / a symbol), **not that "every edge is correct"**; edge-level precision / recall are **both unmeasured** | to be added (largest) |
| 2 | The **64,110** "static only" edges are unclassified (registered-but-uncalled vs not-covered-by-tests) — **currently the largest single black box** | to be added |
| 3 | Call-site anchoring rate 68.48%; the **8,698** unanchored edges are unclassified | to be added |
| 4 | **Layer D trace has 1,069,925 unresolved address entries (79.8%)**, not included in edge statistics → `runtime 45,187` is a **lower bound**; causes (cross-module / dynamic loading / no symbols) **not classified** | to be added (important) |
| 5 | **`before_filter` intermediate graph not archived** → C7's four-segment closure can only "back-derive then verify" (TAUTOLOGY); member-function-pointer probe artifacts not archived → C8 not recomputable | to be added (§5.4) |
| 6 | Runtime edges come from **one** FATE run (9,033 cases) and do not cover the full test surface; `status = reused`, not re-run this round | structural |
| 7 | **Supplementary-test feasibility for the 8,143 "inbound but unreached" is unproven**: 2,492 sampled, **0 hits**, 5,651 unverified → this item **must not be used as "supplementary tests will cover it"** | verified (negative) |
| 8 | Produces no line / branch coverage | design boundary (out of scope) |
| 9 | `file_map` is a lossy "function name → single file" table: attribution of same-named multi-definition functions (**726 names / 3,812 records**) needs address resolution to complete | mitigated (§3.3) |
| 10 | In-graph `def_lines` are **anchor lines near the function body** (sample of 100: 82% exact / 18% offset all within ±8 lines / 0 landing in unrelated code), not exact definition lines | labelled |
| 11 | Assembly layer `asm_functions` (7,420) and `both + source_only` (1,731) have different statistical domains; additionally **x86 86 + aarch64 226** call targets passed as macro arguments remain unresolved | labelled / methods exhausted |
| 12 | Address resolution depends on the build artifact retaining DWARF; after `strip` this capability is lost | prerequisite |
| 13 | Segment ③ of the edge-count closure chain (**64** post-process removals) has no independent counter field; only the two ends close | to be added (§4.2) |
| 14 | Layer C (LLM inference) is off; dynamic function-pointer targets are covered dual-track by `static-reg` (possible) + `runtime` (actual), **with no inference completion** | design trade-off (§3.6) |
| 15 | Layer B `unresolved_by_kind` records only `external_symbol`; the **classification granularity of unresolved edges is insufficient** | to be added |

**On the word "precision"**: the strongest statement this version can make is — **63.7% of runtime edges are independently confirmed by static** (`matched_rate`, `docs/caliber.md` §2.12, not precision); **edge-level precision/recall remain unmeasured**.

### 6.1 Known boundaries that are **not defects** (anti-misreading, important)

The following items are easily misjudged as "data errors" in an audit; all have been ruled out by measurement:

| Item | Value | Why it is not a defect |
|:--|--:|:--|
| **Multi-copy same-named symbols** | **1,047 names / 4,334 nodes** | **all are genuine same-named-in-many-files** — the same function name defined in several files each (`static` scope), e.g. `filter_frame` **263 copies**, `uninit` **261**, `config_input` **179**, `init` **157**. This is FFmpeg's registry-style architecture, **not duplicated data**; true pollution = **0** |
| **Bare-name nodes** | **2,631** | of which `file_map` has **no record for 2,598** (registration symbols / macro products / assembly — structurally no file ownership), the other **33** are multi-copy aggregates (`file_map` lists several files; **no guessing**). **Disambiguable yet left over = 0** ✅ |
| **Nodes without `file_map`** | **2,598** | registration symbols / macro products / assembly — structurally no file ownership; among them the **154** `HAS_INBOUND` are explicitly tagged `gap_evidence="no_file_map"` |
| **Callers with empty `calls`** | **12,260** | only means "out-edges were not collected", **not an error** — leaf functions, functions calling only external symbols, and functions with no call site after macro expansion all look like this |
| **`source=llm` always 0** | 0 | **design state** (`use_llm=false`), not a defect |
| **static-reg 99.4% unique** | 8,571 | **different semantics** (possible vs actual), see §2.5 |
| **Cross-confirmation rate only 26.50%** | 30,259 | **structural result**: unique edges are single-source by definition and cannot be cross-confirmed, see §2.4 |
| **`asm` edges highly unique** | 3,446 / 70.0% | **mechanism-determined**: assembly has no compile-time instrumentation point, runtime cannot record `asm → asm` |

### 6.2 Reproducibility of the denominator chain and known boundaries (including exclusion lists)

> **This section answers**: can `real_denom 31,108` and `target_set 14,375` be computed independently by someone else? **Yes.**

#### 6.2.1 Source of authoritative definitions

| Item | Content |
|:--|:--|
| Definition | this repo's [`docs/caliber.md`](../docs/caliber.md): §2.7 denominator chain / §2.8 implicit definitions / §10.2 `file_map` dual semantics |
| Implementation script | `scripts/denominator_recompute.py` (**shipped with the repo**, same implementation as the numbers here; compute-only by default) |
| Values | `data/denominator.json` (16 fields, same batch as graph `b357bf8e`) |
| Exclusion lists | `data/denominator_excluded_lists.json` (macro 95 / unused 7 / ffprobe 95, checkable entry by entry, see §6.2.3) |

#### 6.2.2 Recomputation result: all 11 fields agree `[measured]`

| Field | Recomputed | Authoritative (`denominator.json`) | Result |
|:--|--:|--:|:--:|
| `instrumentable` | 31,305 | 31,305 | ✅ |
| `macro` | 95 | 95 | ✅ |
| `unused` | 7 | 7 | ✅ |
| `ffprobe` | 95 | 95 | ✅ |
| `real_denom` | 31,108 | 31,108 | ✅ |
| `touched` | 15,571 | 15,571 | ✅ |
| `nt` | 15,598 | 15,598 | ✅ |
| `SIMD` | 1,223 | 1,223 | ✅ |
| `no_inbound_non_simd` | 6,232 | 6,232 | ✅ |
| `with_inbound_in_nt` | 8,143 | 8,143 | ✅ |
| **`target_set`** | **14,375** | **14,375** | ✅ |

**⇒ The denominator chain can be independently recomputed by a third party from the artifacts, without trusting any registered value.**

**Five basis points that must be aligned when recomputing** (missing one puts the result off by tens to hundreds; all from this repo's definition documents):

| # | Basis point | Consequence of getting it wrong |
|:--:|:--|:--|
| 1 | **Node set = `edges.keys() ∪ all callees`** (40,167), not caller side only (38,697) | **32** identities short |
| 2 | **`file_map` dual semantics**: exact key first, **bare-name fallback** (`caliber.md` §10.2) | exact-key lookup only → `instrumentable` collapses to **4,365** |
| 3 | **identity = (bare name, primary file)**, with the `ffmpeg-src/` prefix stripped (`caliber.md` §2.7 + §2.8) | no dedup → double counting; no prefix strip → 658 misjudged as gaps |
| 4 | **Macro test uses the strict form** `(bytestream\|_template\|uops_)` + `^[A-Z0-9_]{3,}$`, **without bare `bits`** | loose form (with `bits`) → falsely removes **1,465** real functions such as `av_get_bits_per_pixel` |
| 5 | **`touched` must be converted to identity first, then `&= instr`** | using bare names directly → `nt` inflated to the 30,000 level |

> All five are backed by definition-document clauses and source comments, not by our interpretation.

#### 6.2.3 Exclusion lists now on disk (closing a historical gap)

Historically the three exclusion lists were local sets inside the script, recording only counts, not entries. **This version writes them out in full**:

| File | Content |
|:--|:--|
| `denominator_excluded_lists.json` | `excluded_macro` **95** / `excluded_unused` **7** / `excluded_ffprobe` **95**, each entry with `func` + `file` |
| `denominator_macro_audit.json` | **entry-by-entry authenticity review** of the 95 macros (back-checked against source for an actual `#define`) — **audit original, shipped with neither the repo nor the release package**; findings in §6.2.4 |

#### 6.2.4 Known boundary: 40 of the 95 "macros" are actually inline functions `[measured]`

We checked all 95 identities judged as macros **back against source, one by one**:

| Verdict | Count | Meaning |
|:--|--:|:--|
| **Confirmed `#define` macro** | **16** | `IS_8x8DCT` / `MB_TYPE_16x16` / `bytestream2_get_ne16` (alias macros) etc. |
| **Actually a function** (definition found in the primary file, no `#define`) | **40** | mostly `static av_always_inline` in `bytestream.h`, e.g. `bytestream2_copy_buffer` L347 |
| Unresolved (neither found in the primary file) | 39 | mostly swscale template instantiation products |

**Key: 32 of these 40 "misjudgements" were already reached by FATE** — they were in `touched` anyway, so excluding them or not **does not affect** `target_set`.

What is really affected is the **unreached** part:

| Item | Count |
|:--|--:|
| Actually a function and **unreached** (truly vanish from `target_set`) | **8** |
| Share of `target_set 14,375` | **0.056%** |

**These 8** (checkable entry by entry):

| Function | File |
|:--|:--|
| `bytestream2_set_buffer` / `bytestream2_set_bufferu` / `bytestream2_size_p` | `libavcodec/bytestream.h` |
| `bytestream_put_str` | `libavcodec/hdrenc.c` |
| `compile_uops_c` | `libswscale/uops_backend.c` |
| `compile_uops_x86` | `libswscale/x86/ops.c` |
| `expand_filename_template` | `fftools/opt_common.c` |
| `sprite_v_template` | `libavcodec/vc1dsp.c` |

> **Characterisation**: this is the **known boundary cost** of the definition rules (`_template` substring / `bytestream` substring / all-caps), **not a violation of the definitions** — the rules are stated in `docs/caliber.md`, and bare `bits` matching was deliberately dropped to avoid falsely removing 1,465 real functions.
>
> **Impact negligible**: corrected, `target_set` would be **14,383**, a **0.056%** difference from the registered 14,375. **This report keeps 14,375 and discloses the difference of 8 here.**

#### 6.2.5 Going further (next rebuild)

| # | Action | Benefit |
|:--:|:--|:--|
| 1 | Change the macro test to "**look up `#define <name>` first; only then call it a macro**", replacing the pure name heuristic | eliminates these 8 (and possibly more UNVERIFIED misjudgements) |
| 2 | Classify the 39 UNVERIFIED entries (swscale template products vs real functions) | makes the macro list 100% evidence-based |
| 3 | Write the `before_filter` intermediate graph or a `postprocess_edge_dropped` field | turns C7 from TAUTOLOGY into a real criterion |
| 4 | Write the member-function-pointer probe artifacts (source of 958 / 2,727) | makes C8 recomputable instead of NOT_RECOMPUTABLE |

> The first two are "definition refinement" with no effect on existing conclusions; the latter two are "reproducibility reinforcement".

---

## 7. Relation to official gcov (basis declaration)

| | Official gcov | This tool |
|:--|:--|:--|
| **Measured object** | **execution counts** of functions / lines / branches | **call relations** between functions |
| **Scope** | **intra-function** (CFG + branch direction) | **inter-function** (who calls whom) |
| **Product** | coverage report | call graph + call-site anchoring |
| Reference values | lines 60.1% (360,016 / 598,916), branches 51.3% (207,110 / 403,783), functions 70.6% (23,331 / 33,035); GCOVR 8.8+main, snapshot **2026-11-11 06:31:20 UTC** | see the sections of §1 |

**This is not "the same quantity, different algorithm"; it is two different quantities.** Official gcov **does not produce a call graph**; this tool **does not produce line/branch coverage**.

**Complementary**: official answers "how much did the tests reach"; this tool answers "who calls whom, who else calls, and which line called whom".
**Complementary ≠ comparable** — they can be read together, not subtracted from each other (prohibitions in §0).

**Version statement**: the official snapshot publishes neither commit nor configure, so the two **do not correspond edge by edge**. Local source and the official snapshot are **73 days** apart; **51** of the official 2,797 files do not exist locally. Any claim of "aligned on the same commit" does not hold.

---

## 8. Reproducibility

### 8.1 Artifact inventory

> The table lists artifacts used in this audit round. `acd_graph.json`, `denominator.json`, `denominator_excluded_lists.json` and `target_set.json` are shipped with the repo or the Release; the rest are internal audit artifacts, **not shipped**, listed only for traceability.

| File | Content | Key fields / anchors |
|:--|:--|:--|
| `acd_graph.json` | the graph (38,697 nodes / 114,175 edges) | `edges` / `file_map` / `meta` / `summary`; md5 `b357bf8e…` (on-disk; report-body original anchor `d690c09e…`) |
| `denominator.json` | denominator authority, 16 fields (12 carry their own definition; definitions for `macro` / `unused` / `ffprobe` / `real_denom` / `touched` are in `docs/caliber.en.md` §2.7) | `values` / `c_layer_target`; md5 `1da5867b…` (redacted distribution copy; audit original `616cb5e3…` same values) |
| **`target_set.json`** | **supplementary-test target set (14,375 entries)** | md5 `5633cb3a…` (bound to `b357bf8e`) |
| `compile_db.json` | translation-unit list (2,257) | `entries` |
| `addr_resolve_full.json` | results of 85,754 address resolutions | `addresses` / `identity_stats` |
| `callsite_coverage.json` | edge-level reconciliation + call-site line anchoring | `edges` / `call_site_line_anchor` |
| `trace_build/edges_fate_20261013_192424_recover.json` | raw Layer D runtime trace | `edges` / `trace_count` / `callee_addr` / `call_site_addr` |
| `verify_c1c8.json` | results of the second-tier 9 criteria (including each item's **verifiable strength**) | `checks` / `summary` |
| **`denominator_excluded_lists.json`** | **full exclusion lists (§6.2.3)**: macro 95 / unused 7 / ffprobe 95 | `excluded_macro` / `excluded_unused` / `excluded_ffprobe` |
| **`denominator_macro_audit.json`** | **entry-by-entry review of the 95 macros (§6.2.4)**: 16 macros / 40 actually functions / 39 unresolved; audit original, not shipped | `counts` / `rows` |

### 8.2 Recomputation scripts

**Shipped with the repo (readers can run them directly)**

| Script | Purpose |
|:--|:--|
| `scripts/denominator_recompute.py` | recompute denominator-chain fields under this repo's definitions (compute-only by default; `--write` persists) |
| `scripts/verify_graph.py` | 16 self-consistency criteria (current graph expected 16/16 PASS) |
| `scripts/export_views.py` | re-export the viewer's three views from the graph |

**Internal audit scripts (not shipped; purposes listed for comparison)**

| Script | Purpose |
|:--|:--|
| address resolution | address → `file::func` + source line (DWARF), read-only |
| edge reconciliation | edge-level reconciliation + call-site line anchoring (see §8.3) |
| closure criteria | 8 closure criteria (distinguishing true criteria / tautologies / non-recomputable) |
| macro audit | entry-by-entry source review of the 95 macros (§6.2.4) |
| number regression | 103 number-regression checks for this report; any mismatch exits non-zero |

> "Number regression" is this report's **release gate** — it guarantees report numbers and artifact numbers never drift apart. That script is not shipped; this repo's equivalent gates are `scripts/verify_graph.py` (16 criteria) and `scripts/denominator_recompute.py` (denominator fields).

```bash
python scripts/verify_graph.py acd_graph.json
# expected: total 16 / PASS 16 / FAIL 0
```

### 8.3 One example (recomputing §5.1)

```
# The reconciliation script is not shipped; below is the expected output
# on the currently bound graph (numbers consistent with §5.1):
#   static-family edges 92,892 / runtime edges 45,187
#   matched = 28,782 / runtime only = 16,405 / static only = 64,110
#   closure: 28,782 + 16,405 = 45,187 True
```

### 8.4 Reproduction prerequisites

| Condition | Explanation |
|:--|:--|
| Graph md5 | must be `b357bf8ea8a4b6bae4892ab99254bf2a` (the one distributed in `release/`; the report-body original anchor `d690c09e…` is not shipped with the repo or the package and is not publicly available) |
| Build artifact | `ffmpeg.exe` must **retain DWARF** (not `strip`ped) |
| Source tree | `818cecc6e…`, path `G:/ffmpeg-src` |
| Line-number consistency | if the source is modified, the reconciliation of `call_sites` against resolved line numbers changes |

---

## 9. Glossary

| Term | Definition |
|:--|:--|
| **identity** | function identity = `file::function name`. The same name in different files is a different identity |
| **bare function name** | function name only, without file. The raw granularity of the runtime trace |
| **instrumentable denominator** | nodes with `file_map` and non-assembly, identity-deduplicated = 31,305 |
| **`real_denom`** | true denominator after removing macro / unused / ffprobe from the instrumentable denominator = 31,108 |
| **`touched`** | the set of function identities hit by the runtime trace |
| **`nt`** (untouched) | `real_denom − touched`, a set difference (not a numeric difference) |
| **`target_set`** | supplementary-test target set = no-inbound non-SIMD + inbound-but-unreached = 14,375 |
| **`source`** | primary-source field (single value, totals 114,175) |
| **`sources`** | all-sources field (array, overlapping, **not additive**) |
| **`static-reg`** | function-pointer registration edges, semantics "**may be called**" |
| **unique edge** | an edge whose `sources` set has exactly size 1 (only one layer can find it) |
| **matched** | static-family and runtime edges existing simultaneously at identity granularity = 28,782 (63.7% of runtime edges). Basis name `matched_rate`, see `docs/caliber.md` §2.12 |
| **anchoring rate** | share of runtime call addresses whose resolved line number agrees with the static `call_sites` = 68.48% |
| **`gap_class`** | five-way label for no-inbound nodes, not a quality conclusion |
| **overkill** | among noise-filtered edges, the count that actually has evidence from another layer = 0 |

---

## 10. Suggested citation

**✅ Safe to cite directly**

- "Built a multi-layer call graph over FFmpeg with **38,697 nodes / 114,175 edges**, of which **30,259 edges (26.50%) are cross-confirmed by ≥2 independent sources**"
- "Multi-layer merging raises edge coverage by **33.1%** over the **strongest single layer** (+28,426 edges); the runtime / asm / static-reg three **paths** together contribute **28,379 unique edges**"
- "**63.7%** of runtime edges are independently confirmed by static parsing (`matched_rate`, `docs/caliber.md` §2.12, not precision)"
- "Anchors call-site source lines onto runtime call addresses, with a **line-level anchoring rate of 68.48%**"
- "Produces a **structured list** of **14,375** 'not reached by tests' functions (of which **8,143** still have callers), giving the uncovered list call-relation information (the denominator chain can be independently recomputed under this repo's definitions, see §6.2)"
- "Typed the no-inbound nodes five ways; **residual true dead code 0**"

**⚠️ Cite with qualifiers**

| Number | Qualifier |
|:--|:--|
| `14,375` / `15,598` | independently recomputable under this repo's definitions (§6.2.2); **known boundary difference of 8 (0.056%) disclosed**; never claim "supplementary tests will cover it" (next row) |
| `8,143` | **a structural annotation, not a proven supplementary-test gain** — 2,492 sampled, 0 hits (§1.1 / §6 #7). **Never say "testing these 8,143 raises coverage"** |
| `114,175` edges | **must be cited per layer** (includes `static-reg` possibility edges + `asm` edges); never call them "actual call edges" |
| `63.7%` | it is `matched_rate` (matched rate, identity granularity, `docs/caliber.md` §2.12), not precision / recall |
| `68.48%` anchoring rate | **not comparable with any other ratio** (numerical coincidence) |
| `runtime 45,187` | a **lower bound** (another 1,069,925 addresses unresolved and not included, §6 #4) |

**❌ Never cite**

- any "coverage X%" (confuses the basis with official coverage)
- "more precise / higher quality than official" (no evidence, see §6 #1)
- "covers X% of official functions" (the numerator is "collected", not "executed" — different semantics)
- "64,110 static edges are wrong" (§5.1 explains the number mixes "registered but not called" and "not covered"; it is not an error count)
- "8,571 static-reg edges actually called" (the semantics is "**may** be called")
- "the LLM layer is not implemented yet" (implemented, validated, **deliberately off**, §3.6)
- "all 9 closure criteria pass" (only **1** of them is independently recomputable, see §5.4)

---

*Numbers marked `[measured]` / `[derived]` whose artifacts ship with the repository can be recomputed from the artifacts and scripts listed in §8. Items that depend on artifacts not shipped here, or that are not independently recomputable, are explicitly marked in §5.4 and §6; no estimated values have been filled in.*
