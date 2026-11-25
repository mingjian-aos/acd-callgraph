# 全量图下载 / Full graph

`acd_graph.json` **不在 git 里**，只随 GitHub Release 分发。仓库内置的查看器只有 3 个切片，不是全图。

- 下载页：[Releases v4.0](https://github.com/mingjian-aos/acd-callgraph/releases/tag/v4.0)
- 压缩包：`acd-ffmpeg-n9.1-dev-b357bf8e.zip` — 5,385,408 B（约 5.1 MiB）
- 解压后：`acd_graph.json` — 106,072,639 B（约 106 MB）
- 图 MD5：`b357bf8ea8a4b6bae4892ab99254bf2a`
- 压缩包 MD5：`2545fb575b7eb5cd305a75d2e8f0f2de`
- 权威清单：[`release/MANIFEST.txt`](release/MANIFEST.txt)、[`release/RELEASE_NOTES-v4.0.md`](release/RELEASE_NOTES-v4.0.md)

**为什么放 Releases：** 106 MB 的 JSON 会永久膨胀 git 历史；Release 让 `git clone` 保持小。

**拿到图之后：** 把 zip 放进仓内 `release/`，或解压后把 `--graph` 指向 `acd_graph.json`。`scripts/query.py` 可以直接读 zip，只用 Python 标准库；缺图时它会明确报出期望的文件名。
