# 复现环境与参数

本页记录“把这张图重跑出来”所需的全部输入。目标不是让所有人跑通，而是让想验证的人**能对齐基线**。

> **本页的权威范围**（先分清再接数字）：
>
> | 内容 | 地位 |
> |:--|:--|
> | §1 源码基线、§2 configure 参数、§4 产物与打包指纹（字节数 / md5）| **本页是权威**，别处没有第二份 |
> | §3、§5 里出现的口径数字（31,305 / 40,167 / 114,175 / 31,500 / 7,420 / 14,375 / 2,933 / 5,638 …）| **引用副本**：定义见 [`caliber.md`](caliber.md)，值见 [`data/denominator.json`](../data/denominator.json) 与报告 §5.2；两处不一致时**以它们为准**，本页不构成第二源 |

## 1. 源码基线（必填）

| 项 | 值 |
|---|---|
| 仓库 | FFmpeg 官方 |
| commit | `818cecc6e1afab932cf4d40ef0d7b8cd40311a17` |
| describe | `n9.1-dev-1030-g818cecc6e1` |
| commit 时间 | 2026-08-30 |
| 平台 | Windows x86_64 / MinGW-w64 |

```bash
git clone https://github.com/FFmpeg/FFmpeg.git
git checkout 818cecc6e1afab932cf4d40ef0d7b8cd40311a17
```

> 换任何一个 commit，节点数与边数都会变，本仓数字不再可比。

## 2. configure 参数（必填）

```
--prefix=G:/ffmpeg-install --disable-doc --disable-debug --enable-gpl
```

该参数取自本机构建目录的 `ffbuild/config.mak`（字段 `FFMPEG_CONFIGURATION`）。

## 3. 各层是怎么来的

| 层 | 输入 | 备注 |
|---|---|---|
| A 宏展开 | `gcc -E` 后的中间源 | 产出并入 B 层 |
| B 静态解析 | 源码，tree-sitter | 解析函数定义 31,500 |
| D 运行时 | 插桩编译 + `make fate` 跑测 | 由引擎内部一键完成，见下 |
| asm | 源码汇编 + Capstone 反汇编 | 入图 asm 函数 7,420 |
| static-reg | 函数指针注册表 | func 2,933 / table 5,638 |

**D 层不需要手工写插桩脚本**：引擎的一条管道负责「插桩编译 → exe 原位替换 → 批量跑 fate → resolve → 合流进图」。全量耗时约 **3.3–3.6 小时**（3,011 个 fate 目标），建议后台跑。

## 4. 关键产物与校验

| 产物 | 说明 |
|---|---|
| `acd_graph.json` | 图本体，106,072,639 B |
| MD5（随附图 / 分母绑定）| `b357bf8ea8a4b6bae4892ab99254bf2a`（2026-11-14）|
| MD5（报告体所依据）| `d690c09ef8f148091e95871452a77259`（2026-11-11，字节差 279 B）|
| `denominator.json` | 触达率分母（31,305），**绑定 b357bf8e**，随仓提供 |
| `denominator_excluded_lists.json` | 三份剔除名单（macro 95 / unused 7 / ffprobe 95），随仓提供 |
| `target_set.json` | 目标集合（14,375），同样绑定本图（体积 1.2 MB，未入库）|

校验分三步：

```bash
# 1) 指纹
md5sum acd_graph.json      # 应等于 b357bf8e…

# 2) 16 项自洽判据（本仓 scripts/verify_graph.py）
python scripts/verify_graph.py acd_graph.json
# 期望输出：总 16 / PASS 16 / FAIL 0

# 3) 分母复算 —— 把触达率分母从头算一遍（本仓 scripts/denominator_recompute.py）
python scripts/denominator_recompute.py \
  --graph acd_graph.json \
  --build-root <构建目录，含 config.h> \
  --asm <asm_capstone_map.json> \
  --touched <edges_fate_*.json> \
  --compare data/denominator.json
# 期望：16 个字段逐项一致；默认只算不写，加 --write 才落盘
```

> 判据期望值是按 `d690c09e` 对齐的。由于新图聚合数字未变，在 `b357bf8e` 上仍 16/16 PASS；若你的图换版本后出现 FAIL，先看是哪条判据，再对照报告 §8.4（复现前置条件）与 §6.2.4（已知边界）。

分母文件与图必须同批生成，跨批混用会导致触达率口径失真。

### 4.1 大产物包（分发用）

大文件不进 git，统一打成一个包放在 **Releases**：

| 项 | 值 |
|---|---|
| 包名 | `acd-ffmpeg-n9.1-dev-b357bf8e.zip` |
| 体积 | 5.14 MB（5,385,408 B；原图 101.2 MB，压率 5.1%）|
| 包 md5 | `2545fb575b7eb5cd305a75d2e8f0f2de` |
| 内含 | `acd_graph.json` + `denominator.json` + `target_set.json` + `MANIFEST.txt` |

> 包内 `denominator.json` 是**脱敏分发版**（1,955 B / md5 `1da5867bafdede493bb3901e4bd7c4a5`，已移除审计、署名与本机路径字段，`values` 未改）；审计原件 7,366 B / `616cb5e3…` 与包内数值逐字段一致，**不随包分发**。

`MANIFEST.txt` 登记每个成员的字节数与 md5，另附运行时可执行产物 `acd_trace_demo.exe` 的指纹——**该 exe 不随包分发**（121.9 MB，且含编译后的 FFmpeg 二进制，分发二进制会引入额外的许可证义务；D 层请自行重跑）。

## 5. 口径纪律（读报告前必看）

完整定义与边界见 [`caliber.md`](caliber.md)。这里只列四条红线：

1. 每个数字标 `[实测]` 或 `[推导]`，`[推导]` 必附公式；
2. **禁跨口径相除**：分母 31,305 与节点 40,167 不是一回事（40,167 = `key ∪ callee` 最宽口径，含外部符号，定义见报告 §5.2；`40,167 − 38,697 = 1,470` 即无对应图内节点的裸名 callee）；
3. 「主源边数」可相加（合计 114,175），「独占贡献」不可与主源相加；
4. 不可复算的项**明确标为不可复算**，不填估计值。

## 6. 待补

- 工具链版本清单（gcc / MinGW-w64 / capstone / tree-sitter / Python）：当前未落盘，公开前补成 `toolchain.lock`；
- 若读者在自己的环境里跑出不同数字，请附 commit + 工具链版本 + md5 提 issue，这类反馈是本仓最想要的输入。
