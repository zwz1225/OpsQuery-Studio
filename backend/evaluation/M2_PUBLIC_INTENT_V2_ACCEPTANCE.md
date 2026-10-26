# M2 public intent v2：条件依据、首次 SQL 复评与关系粒度

日期：2026-10-18。候选策略：`bird_public_intent_candidate_v2`。

## 完成的修改

### 1. 样本只提供覆盖提示

v1 的 `sample_conditions` 把词汇碰撞升级为强制谓词，导致四题被错误修复。v2 的样本匹配仅可提示字段覆盖，输出显式 `mandatory=false / authority=coverage_hint_only`。

覆盖提示只接受未截断、在当前授权字段样本中归属唯一的短大写分类代码，并限制为分类角色字段。人名、表/角色普通名词、纯数字与公式常量、跨字段重复代码均不成为补充依据。这保留 SME→segment 的字段提示；不自动强制 `segment='SME'`。

强制条件只从原始官方 evidence 的显式 `field='value'` 或 `table.field='value'` 中提取，字段归属必须唯一、已授权且已进入图。不确定、例示、否定或 OR 表达式不提升为强制条件。识别 WHERE、CASE、FILTER、单值 IN 及有限的大小写归一化形式。这个保守语法不声称能理解全部英文业务条件，也不是业务 SQL 正确性的充分证明。

`required_profile_conditions` 为旧报告字段名，v2 中其内容已改为有 `unique_public_field_value_binding` 权限标记的显式公开条件；样本提示在 `profile_coverage_hints` 单独记录。

名称规范值探查按 evidence 中的字段映射绑定。Women's Soccer 不再被同时探查为 first_name、last_name。探查继续最多 4 对、1 次 SQL，并占用原有 SQL 工具预算。

### 2. 四条首次 SQL 的独立原生复评

新增 `scripts.rescore_m2_rejected_first4`。它固定读取两份已核对的 v1 报告，从四条 `missing_population_condition` 拒绝轨迹中提取首次生成 SQL。SQL 内容和哈希必须与记录完全相同，不能使用最终错误 SQL，也不自动改写首次 SQL。

它核对原始报告哈希、旧生产代码身份、开发题范围，以及当前执行器、权限、数据读取与原生评分代码仍与旧版本一致。生成/检索/反馈的有意变化独立记录。当前数据库重新验证后，每题执行首次 SQL 和原始 Gold 共 2 次 SELECT，总计 8 次 SQL、0 模型调用。Gold 只留在可信审查进程。

首次 SQL 从未实际执行过，因此报告明确标记 `initial_sql_previously_executed=false`，不会把新结果伪称为已有结果的重放。2026-10-18 下载的 `m2_rejected_first4_native_server.json` 已核对：四题均与冻结 Gold 的原生结果匹配，8 次 SQL、0 次模型调用。0368 的预测与参考浮点值、十六进制表示完全一致。这一结果仅适用于所审查 SQL 与当前数据，不表示任意浮点运算顺序都等价。

### 3. 统计粒度与关系角色

- 从公开 evidence 中的 COUNT(identifier) 与实际单列主键识别实体统计粒度。0201 的 atom_id 因其主键角色得到定位，不把 connected 中的关联字段误认为同一实体主键。
- 在简单且字段归属明确的物理表查询中，若关联目标的连接字段并非单列主键，可能重复统计实体；对 COUNT(key) 或逐行 0/1 指示值求和反馈 `entity_grain_fanout`，提示 distinct 实体计数、去重输入或 EXISTS/半连接。不会全局给所有聚合加 DISTINCT；不确定的复杂 CTE 保持保守。
- BIRD 候选图保留原有连接路径，并加入已选图节点之间的真实 FK 备选边，最多 24 条；补充关联键照旧单列记录。共享 M1 图构建器未修改。
- 每条备选边附当前字段的角色描述。根据公开动作、条件所属表和被请求实体标签提供参与者边的建议。0586 的 votes.userid 不再被首次最短路径遮蔽；最后编辑者、所有者和操作参与者明确是不同角色。边为备选，不要求把它们全部 AND 进 SQL。
- 对参与者查询中明确提到的相关实体标题，给出“参与者标签 + 上下文标题”的显式开发输出建议。它不读取 Gold，不作为普遍自然语言唯一解释，也不强制按某道题答案投影。
- 比例查询保留 REAL 数值路径检查和官方公式提示；乘除顺序本身仅作建议，不触发拒绝或 SQL 改写。服务器复评已证明 0368 的先除后乘表达式可以原生匹配，不能仅凭 AST 运算顺序认定错误。原生评分不加入容差。

这些功能改变的是显式开发候选。实际生成、查询结果和原生 EX 改进都需服务器验证；不能用元数据静态检查代替结果验收。

### 4. 1399 单独记录

见 `evaluation/reviews/m2_reference_shape_1399_20261018.json`。预测单个 Yes 与参考的 YES/NULL 集合不同。状态保持未解决的参考输出形态差异；不修改 Gold、不修改原生评分、不向 Agent 添加题号对应的特殊输出模板。

## 本地验证

- 全部 M2 测试：225 项，222 通过，3 项 Linux 隔离测试在 Windows 跳过。
- 17 项新增测试含四条真实错误修复轨迹、SME 只提示不强制、重复值与字段归属、规范值归属、统计去重、关系角色备选边、首次 SQL 原样执行及异常后的预算/关闭记录。
- 离线准备报告：`evaluation/results/m2_public_intent_v2_preparation_local_20261018.json`，11 项检查通过，包括四题的 8 条首次/Gold SQL 静态只读检查，以及原 7 个原生匹配题的已保存最终 SQL 不被新规则额外拒绝。
- 所有本地 SQL 执行测试使用模拟运行上下文；没有连接 PostgreSQL 或调用模型。测试日志里的 first_sql_native_match 是模拟单元测试输出，不是服务器复评成绩。

## 服务器步骤

**2026-10-18 复评后更新：**下面 A—D 为首次交付时的操作记录。四题无模型审查已经完成，无需重复 B。继续操作请使用 `M2_FIRST4_NATIVE_REVIEW_NEXT.md` 中的新同步包及两份 14 题报告命令；新清单中的 `numeric_policy` 为 `percentage_real_operand_operation_order_advisory_v2`。之前交付 ZIP 和报告保留作为历史证据。

上传 `M2_public_intent_v2_repair_sync_20261018.zip` 到项目根目录。

### A. 同步及回归

```bash
cd ~/Python_work/askdata_studio_ops_release
unzip -o M2_public_intent_v2_repair_sync_20261018.zip
cd backend
python -m scripts.check_m2_public_intent_delivery
python -m unittest discover -s tests -p 'test_m2_*.py' -q
```

### B. 先执行无模型首次 SQL 审查

```bash
python -u -m scripts.rescore_m2_rejected_first4 \
  --source-report evaluation/results/m2_public_intent_diagnostics14_server.json \
  --native-report evaluation/results/m2_public_intent_native14_server.json \
  --output evaluation/results/m2_rejected_first4_native_server.json
```

如果服务器上两份成功报告实际使用 `_v2` 等文件名，把上述 source-report/native-report 改为对应的成功文件。脚本按下列完整 SHA-256 核验内容，不接受失败或不完整的旧报告：

- 诊断：`db2255b9cae7af1a30b24cb9b160c41c7da159bb5ec9b1d9d4fa1dd04e17f246`。
- 原生：`a8e5cb6602277ccde09dcaf0bbb3303dd76339995984e3b4d7f4a9598d30610f`。

先核对这里的结果，确认规则造成的影响，以及 0368 原始乘除路径是否仍有数值差异；这一步不消耗模型调用。

### C. 用新文件名运行相同 14 条开发诊断

```bash
python -u -m evaluation.bird.diagnostic_runner \
  --case-list evaluation/cases/bird_mini_dev/m2_development_diagnostics14.json \
  --model-config-file .env \
  --schema-coverage --intent-candidate --save-snapshot \
  --output evaluation/results/m2_public_intent_v2_diagnostics14_server.json
```

### D. 对本次新生成 SQL 保存独立原生复评

```bash
candidate_sha=$(sha256sum evaluation/results/m2_public_intent_v2_diagnostics14_server.json | cut -d ' ' -f 1)
python -u -m scripts.rescore_m2_intent_candidate \
  --source-report evaluation/results/m2_public_intent_v2_diagnostics14_server.json \
  --source-sha256 "$candidate_sha" \
  --output evaluation/results/m2_public_intent_v2_native14_server.json
```

保留 v1 两份报告和所有原始题集/Gold。输出已存在时使用新文件名，并同步修改复评输入。开发候选会使用新代码身份的索引分区；八域无缓存时预计仍需 49 个共享 embedding 批次，不含重试，另计逐题模型请求。每题 HTTP/生成/校验/SQL/时间/结果限制保持既定上限。

三份新报告分别下载到本地 `backend/evaluation/results/` 后验收。重点检查错误强制条件消失、SME 覆盖保留、0201 粒度、0586 实际关系及上下文输出、1399 原生失败的分类，以及原 7 题是否退化。暂不扩大到 development80 或 holdout，也不宣称 14 题必须全对。
