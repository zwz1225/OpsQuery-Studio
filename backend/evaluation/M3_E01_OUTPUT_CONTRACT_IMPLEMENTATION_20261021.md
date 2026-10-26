# M3 E01：公开输出契约模块与最小接入

日期：2026-10-21（Asia/Shanghai）。**本地实现完成；尚未运行服务器模型对照或计算新的原生EX。**

依据：[A阶段归因](M3_A_FAILURE_ATTRIBUTION_20261021.md)、[首轮实验计划](M3_A_FIRST_EXPERIMENT_PLAN_20261021.md)。A阶段文件中的“尚未实现”是当时状态；本文件记录后续实现。

## 1. 本次实现

| 文件 | 作用 |
| --- | --- |
| [output_contract.py](bird/output_contract.py) | 有限语法提取公开输出请求、绑定已选授权字段或公式，保留原文位置、顺序和歧义；被动观察SQL投影 |
| [case_worker.py](bird/case_worker.py) | 契约加入现有Schema提示；每次SQL生成后记录观察；原验证、执行及修复循环继续运行 |
| [diagnostic_runner.py](bird/diagnostic_runner.py) | 新增默认关闭的`--output-contract`，仅开发诊断使用，且要求`--intent-candidate` |
| [test_m3_output_contract.py](../tests/test_m3_output_contract.py) | 31项公开规则、反例、保存轨迹及真实Agent循环的模拟broker测试 |
| [check_m3_output_contract.py](../scripts/check_m3_output_contract.py) | 对固定开发题的保存SQL离线观察，不执行SQL、不计算EX |

策略ID：`bird_public_output_contract_v1`。

公开请求只接受既定五字段。模块输入是原question/evidence、已经生成的授权Schema图，以及已有公开意图契约中的姓名组；不读取Gold、评分结果、审查JSON、外部文件或样例答案，不根据题号选择规则。

支持主请求与跨句补充输出、公开字段组、公开公式和同义说明。有多个授权字段可对应同一请求时保留候选，不强制选择参考答案中的来源。现有姓名组由原意图契约复用；参与者/标题、单位、精度和粒度策略继续由原路径负责。

语法有意保持有限：单纯筛选上下文和排序辅助量不自动变成投影；only/exclude、定义冲突、未知绑定保留歧义。布尔大小写、额外排名列等未公开约定不作推断。CTE、多SELECT、星号、窗口表达式或无法确定的表达式归属，观察器返回未评估，不输出有效性判决。

## 2. 接入与执行约束

```text
既有授权检索与Schema图
  → 既有v4意图、规范值和单位策略
  → [显式开启时] 构建公开输出清单并加入Schema提示
  → 原隔离Agent的chat
  → 可信侧记录本次SQL的被动投影观察
  → 原validate / 修复反馈 / sql循环
  → 原最终状态与完整原生结果
```

没有修改`isolated_agent.py`、原v4意图规则、检索选择、MCP、在线业务服务或SQL执行器。观察结果不反馈到模型的validation_error，不拒绝SQL，不自动重写SQL或改变结果，也不创建第二套修复循环。

单题时间、模型HTTP、SQL工具和每轮生成/校验预算沿用原策略。观察器不调用模型或数据库；其自身异常只记录`output_observation_unavailable`，不改变SQL验证、执行或重试。Linux隔离仍由原受控子进程与broker承担，本次Windows模拟测试不替代服务器内核验证。

请求标志`output_contract_enabled`必须是布尔值；开启时必须为diagnostic模式并启用原intent候选。在凭据读取前拒绝不兼容标志。没有该标志时，原Agent提示结构、调用和报告字段保持原路径。

## 3. 新报告字段

根运行报告和逐题报告记录`public_output_contract_policy`。逐题另有：

- `public_output_contract`：脱敏后的有序请求、公开原文span、字段/公式绑定、解析完整性和歧义。
- `public_output_contract_complete`：脱敏/截断后是否仍等于实际提示中的契约。
- `public_output_contract_sha256`：实际提示契约的JSON字节摘要。
- `output_contract_observations`：按生成顺序记录sql_round、SQL SHA及被动诊断。

投影诊断可报告`requested_output_not_observed`、`requested_output_order_differs`、`additional_projection_observed`。这些是公开契约提示，**不是SQL有效性、业务正确性或原生EX分数**。公式观察只核对投影引用，不证明算术等价、单位或数值路径正确。

契约最多8项、12KiB；输入超过有限语法长度时保留未解析状态。SQL观察沿用现有解析长度上限；每次生成受原预算约束，报告不新增无限事件。原报告凭据脱敏继续作用于新字段。

## 4. 已完成的本地验证

### 新增专项31项：全部通过

包括：

- 主输出与补充计算项、字段组顺序、公开同义说明及源文本位置。
- only/exclude、纯过滤/排序条件、歧义同名字段、公开定义冲突。
- 姓名组复用、CASE/CAST/ROUND/别名观察、复杂SQL保持未评估。
- 题号变化不改变规则、私有额外输入拒绝、跨来源图拒绝、无文件读取。
- 保存的三道主目标题与20个成功回归题的观察。
- 使用真实Agent应答循环和模拟broker，对比开关前后的提示、SQL、修复反馈、调用次数和预算。
- 诊断发现漏列仍允许原校验和SQL执行；观察器异常不会触发额外调用。
- CLI依赖检查，以及M3代码不能重新冒充原M2冻结候选。

### 相关回归

当前代码共309项：306通过、3项Windows跳过。跳过项是Linux硬超时、文件/网络/进程隔离和真实索引子进程探针，需在服务器候选环境验证。

另6项历史溯源检查在**已保存的实际v4文件**上全部通过。它们断言旧报告仍匹配旧生产者文件；运行时只在历史单元测试上下文将manifest的文件根目录指向v4副本，实际逐文件计算摘要，没有改历史SHA或放宽运行时身份校验。

初次扩展检查曾因当前M3代码与旧生产者不同而触发这6项历史检查；首次失败记录保留，最终结果见[测试记录v2](results/m3_e01_output_contract_tests_local_20261021_v2.json)。不能将这6项描述为M3执行器的现场数据库验证。

### 保存SQL的24题被动观察

见[离线观察报告](results/m3_e01_output_contract_passive24_local_20261021.json)：18题可观察、4题复杂归属未评估、2题语法不适用；三个主目标题各产生一个输出缺口提示，20个成功回归题没有新增缺失提示。

- 0050：根据公开同义说明绑定mailstreet；学校名称来源仍保留授权候选歧义。保存SQL使用street，观察报告不假定两个地址普遍等价。列顺序反例另有单元测试。
- 0085：保存SQL只输出代码，观察到公开百分数输出缺失。
- 0407：保存SQL未输出公开subtypes/supertypes字段组。
- 1479：year没有被有限语法唯一绑定，保留未解析；币种覆盖仍属于A阶段登记的混合问题。

以上没有新模型生成、SQL执行或新EX，不能据此宣称三题已经修复或20题live零退化。

## 5. M2基线与身份保留

修改前已核验并复制原143个冻结交付文件，副本位置记录于[基线保留清单](results/m3_e01_v4_baseline_preserved_local_20261021.json)。该副本是可恢复的代码/交付文件集合，不包含凭据，也不是已配置好的完整独立运行环境。

当前工作树中原冻结路径仅`case_worker.py`与`diagnostic_runner.py`两处作为M3候选修改，其他141处仍保持原摘要；新增output_contract模块使执行文件身份从96变为97。M2原报告、题库、Gold、协议、冻结候选、登记及正式评分控制器保持原样。M3使用新身份，原M2冻结/溯源入口拒绝当前M3代码是预期行为，不能修改旧候选摘要来继续运行。

## 6. 可执行的本地检查

在backend目录：

```bash
python -m unittest discover -s tests -p 'test_m3_output_contract.py' -v
```

离线观察使用新的输出文件名：

```bash
python -m scripts.check_m3_output_contract \
  --case-list evaluation/cases/bird_mini_dev/m3_a_output_contract24.json \
  --output evaluation/results/m3_e01_output_contract_passive24_review.json
```

脚本默认核对已验收v4生成报告的SHA，公开输入按协议摘要核验，只接受development80子集；拒绝保留题号、重复题号、已有输出或覆盖来源文件。输出保存在独立新文件，不修改原始报告。

## 7. 下一步与边界

**本步“模块、最小接入、正反例测试”完成。下一步准备可核验的独立基线/候选运行目录和24题同轮对照脚本。** 需要同时绑定两边的代码/公开配置/来源、校验和索引身份，并自动衔接新生成与独立原生复评，再交付服务器命令。

本次没有提供让用户直接覆盖v4运行目录并重跑的方案，也没有运行正式holdout30。固定24题对照通过后，才按A阶段计划决定完整80题对照；不得把本地投影观察当作模型效果验收。
