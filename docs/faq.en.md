# FAQ · the seven questions we get most

> 中文 → [`faq.md`](faq.md)

## 1. Can you build a graph for my repository too?

**This repository does not contain the build engine**: it ships data, method, verifiers and caliber. Two paths:

- **Wait for the engine-side toolchain**: published separately; this repository does not announce a date.
- **Build it yourself**: follow [`reproduce.md`](reproduce.md) to reproduce the four paths — A (macro expansion) / B (static) / D (runtime) / asm + static-reg — then fuse them by the caliber in [`caliber.md`](caliber.en.md).

If you really have a million-line-scale C/C++ project that is still actively updated (assembly included is a plus), use the [feasibility template](../.github/ISSUE_TEMPLATE/feasibility-request.md) and leave the repo address and scale (lines of code / language mix / assembly or not / update frequency). We reply with **one** feasibility judgement: whether a graph can be produced under the same caliber, a rough effort estimate, and which part is expected to be out of reach. **If we cannot tell, we say so; no scheduling commitments.**

## 2. The md5 of the graph I downloaded differs from the report's — why?

There are two anchors: the report body was written against `d690c09e` (**not shipped with the repo or the package; not publicly available**), and the release asset is `b357bf8e`. The two differ by 279 B (cross-language metadata only); all aggregate numbers match item by item, and the 16 checks pass 16/16 on the new graph. **Always verify against the md5 of the file you actually downloaded**; details in [`anchors.md`](anchors.md).

## 3. Is 49.74% a coverage rate?

No. This repository only uses **function reach rate** (`touched / instrumentable`) — neither line nor branch coverage; calling it coverage invites confusion with gcov's caliber. Definition in [`caliber.md`](caliber.en.md).

## 4. Is a 26.50% cross-confirmation rate too low?

The remaining **73.50%** are single-source edges — by definition they cannot be seen by two paths at once. "26.50% crossed" and "73.50% exclusive" are two sides of the same fact, not "quality is only 26%".

## 5. Can the 8,571 `static-reg` edges be used as actual calls?

No. Their meaning is "**may** be called" (the function is hung on a function-pointer table), all low confidence. Any quote must say "possible, not observed".

## 6. How do I cite or republish?

Use [`CITATION.cff`](../CITATION.cff), and **every number must carry the graph md5 + the FFmpeg commit**. What may be quoted, what must be qualified, and what must not be quoted at all: see report §10.

## 7. Why does the viewer show only a few hundred nodes?

Because **it is not the whole graph**. `viewer/acd-viewer.html` embeds **3 hand-picked slices** (neighbourhoods taken by focus + depth 2/2/3, corresponding to the decode main path, the assembly crosspoint and the unreached blind spot), totalling **414 nodes / 1,147 edges** — only **1.07% / 1.00%** of the full graph's 38,697 nodes / 114,175 edges. The viewer states that ratio in four places: the top-bar badge, the hint under the canvas, the right-panel ledger, and the footer at bottom right.

For the whole graph use `scripts/query.py` (pure standard library, reads the zip directly, no need to unpack the 106 MB), or build your own viewer per [`reproduce.md`](reproduce.md). Why not embed the full graph: all 114,175 edges in a single HTML file would be tens of MB and no browser could draw it.

## Appendix: how big is it really?

**About 2 MB** excluding the release package (documents, scripts, the bilingual viewer, three UI screenshots, one diagram); about 7.5 MB with the release package. The full `acd_graph.json` (106 MB) is not in git and ships via Releases.
