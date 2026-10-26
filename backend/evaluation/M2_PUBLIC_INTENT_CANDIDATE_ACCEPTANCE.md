# M2 通用修复开发候选：实施和复验

日期：2026-10-18。策略：`bird_public_intent_candidate_v1`。

## 本次完成的五项工作

| 顺序 | 实现 | 主要观察对象 |
| --- | --- | --- |
| 1 | 从当前 catalog 判断排序表达式可空性，检查 DESC 的 NULL 优先问题；解析显式 Top-N 和数字序数的大小、方向、offset。支持 ABS、投影别名和排序列序号；显式要求缺失值优先时保留该意图。 | 0050、0082、0036 |
| 2 | 补齐同表编号 first/last name 组；检查输出星号、缺失的姓名槽位和业务分类条件；数量比较和无指定属性的实体列表采用下述明确的开发输出约定。 | 0036、1486、0159 |
| 3 | 根据真实 FK 解释名称与 ID 的角色；对原问题引号中的名称或官方 evidence 的文本等式做受控 LOWER 等值探查，将唯一原生拼写传入模型和校验反馈。 | 1405、0766 |
| 4 | 对百分比提供 REAL 分子在缩放和除法之前转换的生成约定，并检查常见 COUNT 比例的 decimal/final-only-cast 路径。按 evidence 保留是否乘 100；明确要求取整/小数位时不强制此约定。 | 0368，以及比例问题回归 |
| 5 | 支持空基线下有明确字段依据的种子，以及当前基线表两跳真实 FK 内的必要字段；补齐姓名组和明确条件字段；对同名 type/id/amount 等先做表归属消歧。 | 1435、0201、1399、0586 |

实现不包含题号、数据库名或逐题 SQL 替换表。只读取原始 question/evidence、当前授权 catalog 和已有 profile/index。SQL 原样送入 PostgreSQL，所有修改仍由模型在已有生成次数内完成。

### 输出与数值约定的适用范围

- 对“是否更多，如果更多，多多少”且 evidence 给出减法数量公式的独立数量比较，返回一个带符号数值；符号同时表达比较结论。校验拒绝额外的 Yes/No 结果列及把 evidence 的减法包装为 ABS。
- “列出全部某类实体”没有指定属性、且元数据能唯一定位其单列主键时，默认只投影该实体主键。明确请求名称、日期、金额、全部字段等不套用这一约定。无法唯一定位时仅保留一般提示，不伪造确定的输出字段。
- 编号姓名组根据实际字段和 first/last 标签识别，按槽位给出字段组，不加入邮箱。输出组完整性检查属于保守的结构检查，不能证明整条业务 SQL 正确。
- REAL 运算路径属于本次显式的开发生成约定，不是 PostgreSQL 所有比例计算的通用等价规则。原生 EX 继续直接比较 native tuple set，不加入容差、舍入、Decimal/float 强制转换或评分豁免。0368 必须由服务器原生复评确认。

这些约定不修改冻结协议 `m2_pg_v1`。候选只能通过开发诊断的 `--intent-candidate` 开启，正式 live/gold worker 拒绝该开关。正式评测推广需在开发复验后明确冻结候选版本和相应就绪材料。

## 覆盖、预算和诊断

- 保留已有 .55/v1 已选字段及其顺序，在此基础上最多再补 8 个字段，入选字段总数仍至多 20；实际 FK 连接键按原图规则另计。不会声明所有图字段都在这 20 个检索字段内。
- 新字段依据必须能追溯到明确公开字段名、标签、姓名字段组或未截断的授权样本与问题词的匹配。同名字段不能仅凭 FK 可达就补入。仅使用真实声明的外键，不发明 join。
- 每题规范值探查最多 4 个 `(授权文本字段, 原问题/evidence 字面值)`，合并成一次 SQL；每对最多 3 个不同值。唯一匹配、无匹配、歧义分别记录，不把前 3 个值解释为完整字典。
- 查询使用实际 PostgreSQL `LOWER`，报告标记 `unique_database_lower_match`；不声称数据库 LOWER 等同于所有 Unicode 的 Python casefold。
- 探查进入现有 `Budget.sql_call()`，占用原有 3 次 SQL 工具额度中的 1 次，之后最多剩 2 次 SQL 执行轮次。无探查时仍可用 3 次。没有额外模型步骤或扩大的总预算。
- 查询复用既有只读执行器、授权来源校验、明确事务、30 秒 SQL 超时和结果大小限制；失败也保留已用次数、查询哈希和生命周期记录。
- 原始 profile 仍最多 3 个值、文本最多 64 字符；新的探查作为独立候选能力记录，不冒充原始 profile 样本。截断样本不能作为精确业务条件。
- schema 补充原因、provider 实际分数、未进入 rerank 的字段、最终图、意图约定、规范值 SQL/来源/预算、每次校验原因和修复反馈全部记录。未进入 rerank 的字段，报告 `rerank_score=null`，图中的 0 分只是显式元数据补充的占位值。
- 原有修复反馈仍脱敏并受 8192 字节上限约束；重复失败 SQL 会终止，不能用同一错误消耗第三次生成。

## 本地证据与限制

见 `evaluation/results/m2_public_intent_offline_review_local_20261018_v3.json` 和 `m2_public_intent_tests_local_20261018_v3.json`。

本地用原始 14 条公开输入、原有入选字段和已验收授权元数据重放补充策略，检查四条澄清所需字段以及原 SQL 的结构差异。该重放没有本机数据库连接，也没有保存的完整 index profile 样本，因此 **SME 样本匹配、真实规范值、模型是否采纳和原生 EX 均待服务器确认**。

测试使用合成字段、模拟数据库和模型，并覆盖真实 retrieval→Schema 图、broker→隔离 Agent answer loop→修复反馈的集成路径。Windows 无法替代 Linux seccomp/真实数据库探针；服务器脚本会重新执行实际探针。

## 服务器执行

上传 `M2_public_intent_sync_20261018_v2.zip` 到服务器项目根目录。它是在已有 native replay10 版本上的增量包；v2 明确区分 REAL 与 DOUBLE 运算候选，不将二者视为原生 EX 等价。

### 1. 同步并运行本地逻辑回归

```bash
cd ~/Python_work/askdata_studio_ops_release
unzip -o M2_public_intent_sync_20261018_v2.zip
cd backend
python -m scripts.check_m2_public_intent_delivery
python -m unittest discover -s tests -p 'test_m2_*.py' -q
```

### 2. 只跑原有 14 条开发诊断

```bash
python -u -m evaluation.bird.diagnostic_runner \
  --baseline-report evaluation/results/m2_c_bird_development80_server.json \
  --runtime-report evaluation/results/m2_c_bird_runtime_server.json \
  --gold-report evaluation/results/m2_c_bird_gold110_server.json \
  --case-list evaluation/cases/bird_mini_dev/m2_development_diagnostics14.json \
  --model-config-file .env \
  --schema-coverage --intent-candidate --save-snapshot \
  --output evaluation/results/m2_public_intent_diagnostics14_server.json
```

此步骤需要现有模型配置和 PostgreSQL。历史 runtime/Gold 是来源证据；脚本对本次选中域重新检查数据、权限、隔离、预算和超时，不宣称历史材料是新代码的正式就绪材料。

代码身份变化使索引进入新分区；若八域都没有新分区缓存，首次预计 49 个 embedding 批次（不含重试），另有每题检索和生成请求。索引构建有独立预算，不能漏计进总体消耗。仍用既有模型版本、温度和 workers=1。

### 3. 保存一次无模型原生复评

诊断命令完成后，在同一代码版本下执行：

```bash
candidate_sha=$(sha256sum evaluation/results/m2_public_intent_diagnostics14_server.json | cut -d ' ' -f 1)
python -u -m scripts.rescore_m2_intent_candidate \
  --source-report evaluation/results/m2_public_intent_diagnostics14_server.json \
  --source-sha256 "$candidate_sha" \
  --output evaluation/results/m2_public_intent_native14_server.json
```

该步骤只复用已执行 SQL，再读取冻结开发题 Gold 做可信进程内比较，每个可复评题 2 次 SELECT、0 模型调用。它核对来源、代码版本、SQL 原始字节、隔离和预算材料；拒绝 holdout、旧代码、新旧报告混用和输出路径覆盖。未作答/执行失败有明确排除原因，并在额外的 **14 题开发子集分母** 中按未通过计入；不能只报已执行题成功率。

两个新 JSON 下载到本地 `backend/evaluation/results/` 后再逐题核对。若同名文件已存在，请给两个新输出分别使用新的文件名，并把复评的 source-report/哈希对应改为这次实际诊断文件。保留原报告作为修复前证据。

## 验收顺序

1. 先检查来源、真实探针、代码身份、索引来源、每题 SQL 额度及 HTTP/生成/校验额度，确认没有 Gold/历史答案进入 Agent。
2. 看 0050/0082/0036 的首次 SQL、NULL 排序和 Top-N；0036 的六个实际姓名字段是否齐全，是否发生有效修复。
3. 看 1486 的客户群条件和带符号单列差值，0159 的实体输出约定；1405 的名称关联、0766 的唯一规范字面值，0368 的原生结果。
4. 看 1435/0201/1399/0586 是否获得所需字段及真实 FK 路径，澄清是否减少；失败时保留明确原因，不能把“可执行”当作“答案正确”。
5. 比较无模型复评与原来的 2/10 记录，同时检查 0095、1473 是否退化。这是候选开发诊断，不是严格单变量因果实验或正式 development80/holdout 成绩。14 条确认后再决定是否冻结候选并扩大开发集验证。
