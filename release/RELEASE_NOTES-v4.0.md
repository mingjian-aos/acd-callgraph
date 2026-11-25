# Release · v4.0（2026-11-24）· ACD 多源合流调用图

> 本文件是发布正文草稿，上传 Release 时整段粘贴。图与分母的实际字节数、md5 见 `MANIFEST.txt`。

## 附件

| 文件 | 字节 | md5 |
|---|---:|---|
| `acd-ffmpeg-n9.1-dev-b357bf8e.zip` | 5,385,408 | `2545fb575b7eb5cd305a75d2e8f0f2de` |
| └ `acd_graph.json` | 106,072,639 | `b357bf8ea8a4b6bae4892ab99254bf2a` |
| └ `target_set.json` | 1,285,383 | `5633cb3add38fe2210ad09128b627526` |
| └ `denominator.json`（脱敏分发版） | 1,955 | `1da5867bafdede493bb3901e4bd7c4a5` |
| └ `MANIFEST.txt` | 1,138 | `aab1600ff6fe61ad99b8b41b2d99fe65` |

FFmpeg commit：`818cecc6e1afab932cf4d40ef0d7b8cd40311a17`（`n9.1-dev-1030-g818cecc6e1`）

## 这是什么

一张 FFmpeg 9.1-dev 的**函数级调用图**：**38,697 个调用方节点 / 114,175 条边**，由静态解析（含宏展开）、
运行时插桩、汇编反汇编、函数指针注册表四类来源合流。每条边带 `sources` / `confidence` /
`call_sites` / `trace_count`。

## 三分钟验证（只读）

```bash
# 1) 下载本附件到仓内 release/ 目录，然后：
python scripts/query.py --callees av_make_error_string
#   → av_strerror@ffmpeg-src#libavutil#error.c ｜ sources=runtime,static ｜ confidence=high
#     ｜ call_sites=libavutil/error.h:114 ｜ trace_count=772

python scripts/query.py --callers filter_frame
#   → 命中 263 个 id（static 同名定义，逐个列出，不合并）

python scripts/query.py --selfcheck
#   → caller 键 38,697 ／ 边 114,175，PASS（退出码 0）

# 2) 解压后跑 16 项自洽判据
python scripts/verify_graph.py acd_graph.json
#   → 汇总：总 16 / PASS 16 / FAIL 0
```

## 已知边界（先读再引）

- 边级 precision / recall **未测**（报告 §6 #1）。本仓能证的是自洽与可复算，不是准确率。
- 函数**触达率 49.74%** 不是覆盖率：不产出行覆盖 / 分支覆盖。
- `static-reg` 的 8,571 条是"**可能**被调用"（低置信），不得当实际调用引用。
- 2,650 个 `DEAD_SUSPECT` 是**疑似**，未证实；不得称"死代码"。
- 实证范围只有这一个样本：FFmpeg 9.1-dev / MinGW-w64 / x86_64，不外推。

## 引用

CC BY 4.0（文档与数据）/ MIT（脚本）。引用任何数字请同时带**图 md5** `b357bf8e…` 与 **commit** `818cecc6e1`。
机器可读格式见 `CITATION.cff`；可引 / 需限定 / 禁引三档见报告 §10。
