# M2 public intent v3：公开单位与参与者输出组

日期：2026-10-18。候选版本：`bird_public_intent_candidate_v3`。

## 阶段状态

本地完成规则实现、历史 SQL 回归和同步包准备。实际 v3 模型生成及原生结果需在服务器独立运行。上一版 14 条开发诊断为 11/14；两题无模型变体的成功不计入模型成绩。1399 仍保留参考输出形态差异。

## 已审查依据

| 报告 | SHA-256 |
| --- | --- |
| v2 diagnostic14 | 4743a1b3234f358a51684278c093b31baaea26de3bfc3c3b4c110c2863f6ee52 |
| v2 native14 | f0170d51cbcef805c13befc590c101678f5277fe6ef50b76dc7c2667500d7c08 |
| units/context probe2 | 53dac4f839013d289eb458913c38991823f8112fdc0e1061efa38105758d38be |

probe2 的本地审查 303 项全部通过：0201 的 REAL/双精度先缩放路径均原生匹配；0586 仅加标题即匹配。证据只用于可信开发审查和测试，不进入 Agent、检索索引或运行时题号映射。

## 1. 公开百分数单位

新增 `output_units`，策略 `public_percentage_units_v1`，从原始问题和官方 evidence 生成：

- 问题明确要求 percentage/percent，默认输出 0—100 百分数；显式记录 `ratio_multiplier=100` 和问题依据。
- 问题要求 ratio/fraction/proportion，或明确指定 0—1/返回分数，记录未缩放比例。明确的 0—1/分数单位优先于默认百分数。
- 明确要求严格按公式时记录 `formula_defined`，不附加强制缩放。
- 问题要求百分数但 evidence 的 DIVIDE 公式未写缩放时，记录 `question_formula_scale_conflict=true`；本候选可见约定为“evidence 给出基础比例，问题给出百分数输出单位”。原始问题和 evidence 不修改。
- 显式 NUMERIC/DECIMAL 运算、四舍五入要求继续保留。

这是一项公开、版本化开发约定，并非对所有自然语言公式的完整解析。复杂公式、多输出和舍入保持保守提示；无单位问题不自动添加缩放。

### 数值路径与结构化反馈

- 未要求舍入或十进制定点的计数百分数，提示使用 REAL 或 DOUBLE PRECISION 分子，在 SQL 内缩放后除以受保护分母。
- 接受 REAL、双精度两类浮点路径；不再将双精度一概判错。
- 乘除顺序只给建议，不恢复统一拒绝。0368 的正确先除后乘路径继续通过。
- 对能明确识别的简单 COUNT/SUM 指示器比例，核对算术主干上的缩放，缺少/重复缩放反馈 `percentage_output_unit`。
- WHERE、CASE 条件或 COUNT 参数里的 100 不充当输出单位缩放。复杂表达式不凭词汇碰撞强制判错。
- 不改写生成 SQL，不修改结果值、Gold 或原生评分，不引入容差。

## 2. 参与者与动作目标输出组

新增 `participant_output`，策略 `participant_action_target_pair_v1`。这是明确的开发输出约定：在满足全部条件时，输出参与者标签和被明确点名的动作目标标题，参与者在前。

适用条件：

1. 问题请求 which/who/list 的参与者，具有 added/cast/submitted/performed/made/posted 动作，并出现 to/on/for ... title 的动作目标结构。
2. 唯一的参与者角色与唯一输出组可由当前公开文字及授权字段确定。
3. 参与者标签和目标标题已在授权图中；参与者、动作表和目标表具有唯一、真实的当前 catalog 外键，端点键也在图中。
4. 问题未明确限定 only、排除标题等，也不是计数问题。

适用时，缺列反馈 `incomplete_participant_context_output`；两个直接投影列顺序颠倒反馈 `participant_context_output_order`。字段只在 WHERE/JOIN 中出现不算已输出。

仅用于筛选的上下文、只返回姓名、排除标题、关系不唯一、字段不在图中或无法定位 CTE/复杂投影字段归属时，不升级为强制输出。现有关系角色仍为备选边，不将多条外键全部 AND 进 SQL。保留模型自行选择 LIKE/ILIKE 及必要去重的职责。

## 3. 来源、版本及测试

- 新的 `units_output.py` 纳入代码身份和索引身份；本轮代码变化使索引使用新分区，保持来源和缓存隔离。
- 执行器、权限、数据库数据、原生评分、隔离和模型/SQL预算不修改。旧报告、冻结协议和题集保留。
- 已验收 v2 报告绑定 v2 代码。历史审查测试在验证执行/评分代码未变后，显式模拟原生产者版本；生产审查入口继续拒绝跨候选版本混用。
- 新增测试覆盖单位冲突、显式覆盖、无缩放/重复缩放、常数位置、两种浮点类型和顺序、输出组边界、真实外键、字段授权、题号不变性及旧 11 条成功 SQL。
- 对服务器 probe2 中已匹配的 6 个诊断变体作静态约束回归，它们仍通过。此回归不重新执行 SQL，也不替代新生成验收。
- 所有本地模型和数据库执行测试使用模拟对象；本地未调用模型或连接 PostgreSQL。

## 4. 服务器同步与测试

上传 `M2_public_intent_v3_sync_20261018.zip` 到服务器项目根目录，执行：

```bash
cd ~/Python_work/askdata_studio_ops_release
unzip -o M2_public_intent_v3_sync_20261018.zip
cd backend
python -m scripts.check_m2_public_intent_delivery
python -m unittest discover -s tests -p 'test_m2_*.py' -q
```

检查使用 `evaluation/m2_public_intent_v3_delivery_files_20261018.json`。代码包只更新本轮代码、测试、说明和清单，不含 .env、凭据、题集或原始服务器报告。

## 5. 新版相同 14 题诊断

```bash
python -u -m evaluation.bird.diagnostic_runner \
  --case-list evaluation/cases/bird_mini_dev/m2_development_diagnostics14.json \
  --model-config-file .env \
  --schema-coverage --intent-candidate --save-snapshot \
  --output evaluation/results/m2_public_intent_v3_diagnostics14_server.json
```

代码/索引身份更新后，八域无缓存时预计仍需 49 批共享 embedding，逐题 HTTP 和重试另记。每题生成、校验、HTTP、SQL 及结果预算沿用原上限。

## 6. 对新版 SQL 保存独立原生复评

```bash
candidate_sha=$(sha256sum evaluation/results/m2_public_intent_v3_diagnostics14_server.json | cut -d ' ' -f 1)
python -u -m scripts.rescore_m2_intent_candidate \
  --source-report evaluation/results/m2_public_intent_v3_diagnostics14_server.json \
  --source-sha256 "$candidate_sha" \
  --output evaluation/results/m2_public_intent_v3_native14_server.json
```

两次运行之间保持同一代码和依赖环境。输出若已存在，换新名字，并同步修改后续 source-report 与哈希计算路径。原始 v2、probe2 作为独立证据保留，当前 v3 不重新执行绑定旧代码的历史审查命令。

下载两份新报告到本地 `backend/evaluation/results/` 后核对：

- output_units 的单位、公式冲突和缩放依据是否正确，0201 是否保留实体粒度并生成匹配数值路径。
- participant_output 的唯一外键与字段依据、0586 是否完整投影参与者和标题。
- 原 11 条成功题是否退化，0368 是否仍避免操作顺序误拒绝。
- 每次生成、修复反馈、执行与预算记录是否完整；确认评分和 Gold 未改变。
- 1399 继续按冻结评分记录，不做标签或 NULL 归一化。

本轮保持相同开发子集，后续扩大范围以本次真实生成和原生结果为依据。
