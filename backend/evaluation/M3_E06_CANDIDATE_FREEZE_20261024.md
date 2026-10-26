# M3 E06 候选冻结与 development80 扩展

日期：2026-10-24。E06 24 题审查见 [M3_E06_PAIR24_ACCEPTANCE_REVIEW_20261024.md](M3_E06_PAIR24_ACCEPTANCE_REVIEW_20261024.md)。该轮基线 22/24、候选 23/24；仅 0239 错转对，0206 未误拒，成功回归 20/20。比较报告 SHA-256：`a66d55d54dc22d5bd0cfbec4ba8415a3f507d8c46a9f589aa1c1e7292a8e0d37`。

本次只冻结并准备 **公开 development80** 同轮对照，尚未在服务器执行 80 题。来源为已接受的 E06 24 题包 `b0d2526fed45f2ad3c54f723afb1390930a826764e029ac0c6283f93a3d5b0bc`。新包内基线 100、候选 101 个生产代码文件的路径与 SHA-256 均与原包两侧逐一相等。相对于基线，候选仅改变 `evaluation/bird/case_worker.py`，新增 `evaluation/bird/endpoint_validation.py`。两侧均保留 E05 公开端点提示、E02 条件/关系上下文和相同的进程内 DNS/HTTPS 连接层；不纳入 E03、E04 或其它独立实验的代码。

冻结交付包：`M3_E06_pair80_endpoint_feedback_v2_20261024_r2.zip`，SHA-256：`e64bf68313813ce72f528daeca7cd77871b6ba5b436697830bf03a0a0fea20c2`，包 ID：`012c86dbc14a03f6d42aeffaf8d217099febcb6ac1c862b1fc72970e9fd7c7f1`。仅使用 **r2**；较早的同名无后缀本地制作件是冻结前草稿。包内无 `.env`、数据库密码或数据转储。

题单为原协议 `evaluation/cases/bird_mini_dev/m2_pg_v1/development80.json` 的原始 80 题顺序。冻结原有 20 条回归题和 M2 v4 原生复评报告中的成功 50 题；后者证据 SHA-256：`1bbb278d0a5ffb99b3049faff6e1da2c482230284188e71e8d4fb44504c38774`。模型配置、来源绑定、权限、索引策略、生成与 SQL 预算、原生评分规则沿用原包；仅换题单与同轮控制器。两侧各一次 80 题生成，各自构建 8 域索引；完成两份捕获后分别无模型原生复评。单工作区最多 160 次题目生成，不自动续跑或访问 holdout。

## 预定筛选与人工审查

- 固定分母 80，未回答题计错。候选至少 51/80、超过同轮基线，0239 原生正确；20 条指定回归与历史 50 条成功题全部保持。任一门槛失败仍保存完整报告并逐题分析，不改变分母、阈值或题目。
- 0206 原生正确且不被端点反馈误拒；审查候选全部 `candidate_repair`，确认它们仅发生在公开证据确实唯一指定端点的形态。逐题检查新增由对变错、来源身份、授权 Schema、SQL 尝试、结构化反馈与重生成。
- 同轮 `chat` Token 与逐题 p95 延迟不超过基线的 120%；总 Token、模型 HTTP 请求和索引成本单列。未知成本不能算通过。
- `automatic_screen_pass` 只是工程筛选。即使为真，仍需人工审查 0239、0206、0072 及全部正负变化，才能决定是否接纳。此轮属于开发集诊断，不是正式 EX 或保留集复测。

本地无模型测试：`python -m unittest tests.test_m3_e06_pair80_bundle -v`，3 项通过；覆盖生产代码逐文件复用、80 题与冻结身份、0206 误拒和回归检测、两侧隔离及密钥不复制。服务器操作见 [M3_E06_PAIR80_SERVER_RUNBOOK_20261024.md](M3_E06_PAIR80_SERVER_RUNBOOK_20261024.md)。
