# 两个锚点：为什么并存，怎么自己核

| 锚点 | 是谁 | 状态 |
|---|---|---|
| `d690c09ef8f148091e95871452a77259` | 报告体（`report/`）写作时依据的图，106,072,360 B，2026-11-11 | **不随仓、不随 Release 分发**（不对读者开放）|
| `b357bf8ea8a4b6bae4892ab99254bf2a` | 发布包实物，106,072,639 B，2026-11-14 | 随 Release 分发，可下载 |

**为什么可以并用**：两者字节差 279 B，差异只在跨语言元数据；聚合数字（边、节点、来源分账、缺口五类、置信档）逐项一致；16 项自洽判据在新图 **16/16 PASS**。

**怎么自己核**（只读；前两条约 2 分钟，第三条需构建目录）：

```bash
python scripts/verify_graph.py acd_graph.json    # 期望：总 16 / PASS 16 / FAIL 0
python scripts/query.py --selfcheck              # 期望：caller 键 38,697 / 边 114,175
python scripts/denominator_recompute.py --graph acd_graph.json --build-root <构建目录> --asm <汇编表> --touched <edges_fate_*.json> --compare data/denominator.json
```

**边界（先说清）**：报告体的 103 项数字**无法**对着 `d690c09e` 做逐字节复核——那份文件不公开。能做的复核只有两种：用 `b357bf8e` 复算、看聚合是否与报告一致；以及上面三条判据。若你认为这不够，走 [数据 / 口径质疑模板](../.github/ISSUE_TEMPLATE/data-caliber-question.md)，写明你要复核哪一项、期望值与实得值。

> `b357bf8e` 的 md5 与字节数见 [`release/MANIFEST.txt`](../release/MANIFEST.txt)；下载后先验 md5，再谈数字。
