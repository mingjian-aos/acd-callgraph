# 验证状态 / Verification

> **这不是第三方独立审计。** 这是**可复现的自洽校验**：脚本、命令和本次输出都在仓库里；输入图从 Releases 下载。内部逐版审计记录不公开。对外请说“可复核的验证”，不要说“已审计”。

**验证日期：** 2026-11-26（CST）  
**验证对象：** `acd_graph.json`，106,072,639 B

- 图 MD5：`b357bf8ea8a4b6bae4892ab99254bf2a`
- 图 SHA-256：`743b8f3a45b2c6beb6a13803bf6e28b0a939a6521c2212ac4d0fe08851bee194`
- Release 压缩包：`acd-ffmpeg-n9.1-dev-b357bf8e.zip`，5,385,408 B
- 压缩包 MD5：`2545fb575b7eb5cd305a75d2e8f0f2de`
- 压缩包 SHA-256：`64df005d2e90280c0f430e671db307ab427e081a9ce31052468bac008d72d09e`
- FFmpeg commit：`818cecc6e1afab932cf4d40ef0d7b8cd40311a17`

## 本次结果

| 检查 | 结果 | 日志 |
|---|---|---|
| `verify_graph.py` — 16 项自洽判据 | **16/16 PASS，FAIL 0** | [`verify_graph.txt`](docs/verification/2026-11-26/verify_graph.txt) |
| `verify_matched_rate.py` — 互证率 7 项，含负例 | **7/7 PASS** | [`verify_matched_rate.txt`](docs/verification/2026-11-26/verify_matched_rate.txt) |
| `query.py --selfcheck` — caller 键 / 边总数 | **PASS：38,697 / 114,175** | [`query_selfcheck.txt`](docs/verification/2026-11-26/query_selfcheck.txt) |
| `smoke_test.py` — CLI 回归 + 脚本编译 + 双语/数字一致 | **13 项，FAIL 0** | [`smoke_test.txt`](docs/verification/2026-11-26/smoke_test.txt) |

关键输出：

```text
verify_graph.py    汇总：总 16 / PASS 16 / FAIL 0
verify_matched_rate.py    7/7 PASS
query.py --selfcheck    结论：PASS
smoke_test.py    汇总：13 项，FAIL 0
```

## 自己跑一遍

先从 [Releases v4.0](https://github.com/mingjian-aos/acd-callgraph/releases/tag/v4.0) 下载 zip，解压出 `acd_graph.json` 放到仓库根目录（或把命令里的路径改成实际位置）：

```bash
python scripts/verify_graph.py acd_graph.json
python scripts/verify_matched_rate.py acd_graph.json
python scripts/query.py --graph acd_graph.json --selfcheck
python scripts/smoke_test.py
```

期望结果就是上表四项；`verify_graph.py` 与 `verify_matched_rate.py` 的期望值绑当前图，若图 md5 变了必须先重新对齐判据。

## 这份验证覆盖什么

- 图内部是否自洽：边数、节点数、`reg_table`、自环分类、`gap_class` 五类、`asm` 合流计数等。
- 静态族与运行时边的互证率是否闭合，并用裸名 join 作为负例。
- CLI 的查询、缺图、退出码、`--json` 结构，以及脚本可编译、查看器双语与中英文数字一致。

**不覆盖什么：** 边级 precision / recall 未测；这不是行/分支覆盖率；也没有第三方独立复算。完整口径与已知边界见 [`docs/caliber.md`](docs/caliber.md)，报告见 [`report/`](report/)。
