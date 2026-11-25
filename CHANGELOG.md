# 变更记录

对外可见的版本变化。内部审计台账不在此列；数字与口径以 `data/denominator.json` 与图为唯一源。

## v4.0 — 2026-11-24

**发布形态**

- 首个对外版本：报告 `v4.0`、图锚 `b357bf8e`、三栏查看器、`scripts/` 六个脚本（`query.py` 查询 CLI 与 `smoke_test.py` 回归测试为本次新增）。
- 新增只读查询 CLI `scripts/query.py`（`--callees / --callers / --edge / --selfcheck`，纯标准库，直读发布 zip，不必解压）。
- 全图与分母随 Release 分发（zip 5,385,408 B / `2545fb57…`）；git 内永远没有 106 MB 的图。

**口径**

- 术语统一为「多源」（此前出现过"三层 / 六源 / 五路"的写法）；来源四类 = `static` / `runtime` / `asm` / `static-reg`。
- 数值唯一源 = `data/denominator.json`；`docs/caliber.md` 刻意不含数值表。
- 新增 `scripts/verify_matched_rate.py`（互证率 7 条判据，含负例）。
- 引用纪律分三档：可引 / 必须带限定 / 禁止引用，见报告 §10。

**数据**

- 图锚 `b357bf8e`（106,072,639 B）；报告体原锚 `d690c09e` 标记为**不随仓、不随包分发（不对读者开放）**，复核路径见 `docs/anchors.md`。
- 分母换为脱敏分发版（1,955 B / `1da5867b…`），`values` 逐字段未改；审计原件不随包。
- 目标集 `5633cb3a…`（14,375 条）。

**文档与上架准备**

- 新增中文导读 `导读.md`（八节）与英文 `README.en.md` / `GUIDE.en.md`。
- 新增英文版方法文档 `docs/caliber.en.md`（口径与边界全文）与 `docs/faq.en.md`（七问）；两对文档的数字与中文版逐项相同，`smoke_test.py` 有机器门禁。
- 新增英文版报告 `report/ACD-ffmpeg-report-v4.0.en.md`：章节编号、表格、全部数字与中文版逐条对齐（含 §8.3 对账示例已按 §5.1 现行数更新）。
- 新增 `docs/faq.md`（七问，含「查看器为什么只有几百个节点」）、`docs/anchors.md`（双锚点与复核路径）、`CITATION.cff`。
- issue 只开两条通道（数据 / 口径质疑、建图可行性咨询），模板在 `.github/ISSUE_TEMPLATE/`；空白 issue 关闭；**暂不接受 PR**，修改先走 issue。
- `LICENSE-MIT.txt` 版权主体写明为 **小鹏 (Xiao Peng)**；联系邮箱只放在 `CITATION.cff` 的作者字段，许可正文不含邮箱；`LICENSE` 增「署名与版权主体」一节（换成公司名只需改两行）。
- 报告 §6.2.3 / §8.1 标注 `denominator_macro_audit.json` 为审计原件、不随仓分发，不再指向仓里没有的文件。
- 双许可拆分为标准文本：`LICENSE-MIT.txt`（脚本）、`LICENSE-CC-BY-4.0.txt`（文档与数据），`LICENSE` 为索引。

**查看器**

- 中英双语：单文件 `viewer/acd-viewer.html` 内建 `I18N{zh,en}`（约 100 键，两侧键集相等）与 `TR()` 取词，顶栏 `中 / EN` 运行时切换；语言按 `#lang=` > `localStorage` > `navigator.language` 解析，`permalink` 会带上 `lang`。
- 切片标注补齐：内置 3 个切片共 414 节点 / 1,147 边，占全图 38,697 / 114,175 的 **1.07% / 1.00%**；顶栏徽标、画布下提示、右栏账目、页脚右下四处同标，导出的 PNG 水印同步。
- `scripts/export_views.py` 视图规格扩为 8 元组，产物多写 `title_en / note_en`。

**验证**

- `scripts/verify_graph.py` 在发布图上 **16/16 PASS**；`scripts/query.py --selfcheck` 报 **38,697 / 114,175**。
- `scripts/smoke_test.py` 扩到 **13 项**（新增：查看器 `zh/en` 键集相等、每个视图都有 `title_en/note_en`、产物与模板同源、中英方法文档数字一致），13/13 PASS，不依赖全图；配最小 CI。
