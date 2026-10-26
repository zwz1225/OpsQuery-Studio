# M2 A：BIRD Mini-Dev 数据下载与版本核实

核实日期：2026-10-15。完整数据库包已下载，大小、ZIP 目录、全部文件 CRC 及 PostgreSQL SQL 文本检查已完成。**用户反馈腾讯电脑管家扫描完成、未发现威胁；据此已选择性解压 79 个所需文件，逐文件 SHA-256 全部通过。** 扫描结论来源为用户反馈，未独立读取腾讯扫描日志。来源清单及完整性报告保留各自生成时的状态，见 [来源清单](results/m2_a_source_inventory_20261015.json)、[本地完整性记录](results/m2_a_archive_integrity_20261015.json)；本地获取证据见 [本地数据就绪记录](results/m2_a_data_ready_20261015.json)和[本地检查说明](M2_A_LOCAL_ARCHIVE_REVIEW.md)。随后已完成 [M2 A 固定题集与评测协议 v1](M2_A_EVALUATION_PROTOCOL.md)，冻结 80 道开发题、30 道数据库隔离的保留题和开发集内 smoke8，14 项专项测试与独立重建复核通过。数据库导入和 Gold 尚未开展。

## 当前需要下载什么

**`minidev_0703.zip` 已下载完成，无需重新下载。** PostgreSQL 当前题目与数据集说明也已下载到本地并计算 SHA-256。

| 材料 | 已核实大小 | 状态 / 用途 |
| --- | ---: | --- |
| 官方完整包 `minidev_0703.zip` | 799,944,582 字节，约 762.9 MiB | 已下载且 CRC 通过；用户反馈扫描无威胁；所需 79 个文件已解压并核对摘要 |
| 当前 PostgreSQL 题目 `mini_dev_pg-00000-of-00001.json` | 283,551 字节 | 已保存；500 题、11 个逻辑数据库，作为后续选题和 Gold 的来源 |
| 冻结版本的数据集说明 `README.md` | 10,737 字节 | 已保存；数据集卡声明 `cc-by-sa-4.0` |

官方下载页：<https://drive.google.com/file/d/13VLWIwpw5E3d5DUkMvzw7hvHE67a4XkG/view>。该入口来自[官方 GitHub README](https://github.com/bird-bench/mini_dev/blob/main/README.md)及[Hugging Face 数据集说明](https://huggingface.co/datasets/birdsql/bird_mini_dev)。下载时保留文件名 `minidev_0703.zip`。

不选用 README 顶部旧的阿里云 `minidev.zip`：其响应大小为 800,943,648 字节，HTTP 最后修改时间为 2024-06-20；本次选用官方更新说明链接的 2025-07-03 完整包，并配合冻结版本的 Hugging Face 题目。

## 本地放置目录

目录已创建，原始数据放在项目外的 `E:\PythonLearn\datasets\bird_mini_dev\`，报告留在项目的 `backend/evaluation/`。

```text
E:\PythonLearn\datasets\bird_mini_dev\
├─ downloads\
│  └─ minidev_0703.zip                       ← 已下载并完成完整性检查
├─ releases\
│  └─ hf_f65faf4ae3b638c1fa6df1d3370c8d92c8366301\
│     ├─ mini_dev_pg-00000-of-00001.json     ← 已下载的当前 PostgreSQL 题目
│     ├─ README.md                          ← 已下载的官方说明
│     └─ source_metadata.json               ← 已保存的官方仓库元数据
├─ reference\
│  └─ minidev_0703\                         ← 已核对的小型包内文件与版本差异
└─ extracted\                              ← 已选择性解压所需 79 个文件
   └─ minidev\
      ├─ MINIDEV_postgresql\BIRD_dev.sql
      └─ MINIDEV\                          ← 字段说明、表关系和包内旧题目对照
```

完整包目标路径为：

```text
E:\PythonLearn\datasets\bird_mini_dev\downloads\minidev_0703.zip
```

下载完成后，在本地 PowerShell 执行以下命令可以查看大小和计算完整文件摘要：

```powershell
Get-Item -LiteralPath 'E:\PythonLearn\datasets\bird_mini_dev\downloads\minidev_0703.zip' |
    Select-Object Name, Length

Get-FileHash -Algorithm SHA256 -LiteralPath 'E:\PythonLearn\datasets\bird_mini_dev\downloads\minidev_0703.zip'
```

本地 `Length` 已核对为 `799944582`。完整包 SHA-256 已计算为：

```text
aeb211c0e39010bbdae3838bb5e8bd27dc446ed77495b1709f85ccc9bf67f2be
```

该值是本地文件的记录值，尚无官方 SHA-256 可供独立对照；它用于固定后续使用的数据包。CRC 和大小检查不能替代病毒扫描。

## 选择性解压的范围

已通过 HTTP Range 读取 ZIP 中央目录，共 246 个 ZIP 条目；这里包含目录和 macOS 附加文件，并非 246 个有效业务文件。全包展开约 3.296 GiB。PostgreSQL 首轮仅需要下列 79 个文件，合计 1,002,510,820 字节，约 956.1 MiB。

| 包内路径 | 数量 / 展开大小 | 用途 |
| --- | --- | --- |
| `minidev/MINIDEV_postgresql/BIRD_dev.sql` | 1 个，1,001,882,533 字节 | PostgreSQL 数据与表结构，约 955.5 MiB |
| `minidev/MINIDEV/dev_tables.json` | 1 个，158,301 字节 | 官方原始逻辑表关系说明；需再与 PostgreSQL 物理字段核对 |
| `minidev/MINIDEV/dev_databases/*/database_description/*.csv` | 75 个，合计 76,887 字节 | 字段含义及取值说明 |
| `minidev/MINIDEV/mini_dev_postgresql.json` | 1 个，283,525 字节 | 旧题目版本的对照证据 |
| `minidev/MINIDEV/mini_dev_postgresql_gold.sql` | 1 个，109,574 字节 | 旧 Gold 版本的对照证据 |

MySQL 的 SQL、11 个 SQLite 数据库、`__MACOSX` 和 `.DS_Store` 不在本次解压范围。原始压缩包继续保留，所选文件已解压到 `E:\PythonLearn\datasets\bird_mini_dev\extracted\`。

上面的数量与大小最初来自 ZIP 目录。下载后已完整读取 219 个非目录文件，CRC 全部通过；目录与此前远程读取的 246 个 ZIP 条目一致。所选 79 个文件均已计算 SHA-256，包括完整 PostgreSQL SQL。收到用户扫描无威胁的反馈后，已再次核对原始包 SHA-256 未改变，随后解压并核对全部 79 个文件的大小和 SHA-256，未发现额外解压文件。

## 题目版本与答案格式

官方 Hugging Face 仓库固定在提交：

```text
f65faf4ae3b638c1fa6df1d3370c8d92c8366301
```

仓库元数据的最后修改时间为 `2026-01-18T08:44:25.000Z`。固定版本题目链接：

<https://huggingface.co/datasets/birdsql/bird_mini_dev/resolve/f65faf4ae3b638c1fa6df1d3370c8d92c8366301/data/mini_dev_pg-00000-of-00001.json>

已下载题目的 SHA-256：

```text
7fa740ef9225389cff6c34432120e8325d0ca3008d73db1ae38731234bc10da7
```

该文件是 JSON 数组，实际核对为 500 道题、500 个不同的 `question_id`。每项有 `question_id`、`db_id`、`question`、`evidence`、`SQL`、`difficulty` 六个字段。`SQL` 是 PostgreSQL Gold SQL；并没有随题附带一个可直接当作标准结果的固定结果表，后续应在已验证的数据上执行 Gold。Agent 仅接收协议允许的问题、evidence 与授权 Schema，Gold SQL 仅交给评分器。

当前 11 个逻辑数据库的题数为：

| db_id | 题数 |
| --- | ---: |
| `debit_card_specializing` | 30 |
| `student_club` | 48 |
| `thrombosis_prediction` | 50 |
| `european_football_2` | 51 |
| `formula_1` | 66 |
| `superhero` | 52 |
| `codebase_community` | 49 |
| `card_games` | 52 |
| `toxicology` | 40 |
| `california_schools` | 30 |
| `financial` | 32 |

难度字段实际计数为 simple 148、moderate 250、challenging 102；本记录使用实际文件计数。

**当前 Hugging Face 题目与 2025-07-03 包内题目确有一题 SQL 差异。** `formula_1` 的 `question_id=879`：包内按 `fastestLapSpeed` 直接排序，当前题目改为 `CAST(T2.fastestLapSpeed AS DOUBLE PRECISION)` 后排序。其余题目按完整 JSON 对象比较相同。后续使用当前 Hugging Face `SQL`，包内旧题目及旧 Gold 文件保留作审计，不作为当前 Gold 执行输入。差异已保存在 `reference/minidev_0703/question_version_diff.json`，也写入来源清单。

## PostgreSQL 导入前需要处理的事实

首次远程核实时读取压缩后前 65,536 字节，解压出 383,381 字节的 SQL 开头；后续本地检查已完整读取 SQL。观察到：

- 这是 PostgreSQL 14.12 生成的纯文本 dump，包含 `CREATE TABLE` 和 `COPY ... FROM stdin`，不是 `pg_restore` 的自定义格式文件。
- 表结构部分有 75 条 `CREATE TABLE public...`；11 个 `db_id` 的表汇集在一个 `public` schema，`db_id` 不能直接当作物理数据库名。
- 存在指向原作者角色的 `ALTER TABLE ... OWNER TO ...`，需在受控导入阶段处理所有权；当前服务器只读账号不应直接执行导入。

完整 SQL 已做文本模式检查，见[本地检查说明](M2_A_LOCAL_ARCHIVE_REVIEW.md)，源 COPY 数据计数为 3,898,114 行。导入实施仍需处理所有权、权限和会话设置，在独立 M2 目标中导入，再建立 `db_id → 授权表集合/来源身份` 的映射。Agent 不应因物理上位于同一 `public` 而看见全部 75 张表。当前尚不证明 PostgreSQL 16 导入成功、目标数据一致、Gold 可执行或来源隔离通过。

完整 SQL 约 956 MiB 不等于数据库导入后的占用：数据页、索引、WAL、临时文件另需空间。下载后先在本地核验，再确定需上传服务器的材料，并重新检查服务器磁盘空间。

许可声明来源是冻结的官方数据集卡 `license: cc-by-sa-4.0`；保留来源、提交和说明文件。具体原始数据库附带的说明随数据保留，后续再核对。
