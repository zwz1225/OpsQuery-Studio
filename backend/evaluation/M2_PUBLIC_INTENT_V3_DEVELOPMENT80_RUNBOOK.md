# M2 v3：完整 development80 验证步骤

日期：2026-10-18。使用已通过 14 题定向检查的同一 v3，扩大到冻结 development80；生成和评分继续分离。

## 1. 已确认的前提

- 现有 diagnostic_runner 接受 1—80 个 development80 ID；现有候选原生复评入口支持 80 题，并将未回答病例留在全量分母中。
- 现成清单为 `evaluation/cases/bird_mini_dev/m2_pg_v1/development80.json`，80 个唯一 ID，8 个数据库各 10 题，与原始 80 题基线顺序相同。
- 清单 SHA-256：`237b6f09f8b7ee9965f9e18b3ab2195a79b5ad949e55e6d56868a3266df29b10`。
- 当前 v3 文件与刚通过的 diagnostic14 代码一致，模型及来源也与原始 development80 记录一致。本轮不需要新同步包或代码改造。
- 14 题当前覆盖全部 8 个数据库。索引、代码和来源未变化且缓存完整时，80 题可以复用相应索引，新增共享 embedding 请求应为 0；实际以 cache_hit/model_usage 记录为准。

## 2. 固定比较口径

原始基线为 `evaluation/results/m2_c_bird_development80_server.json`，SHA-256 `7f59478b5d589a49d85027e965e8b3596416ac998df4618c655984841fc8c01d`：

| 指标 | 原始基线 |
| --- | ---: |
| 全部题数 | 80 |
| 原生通过 | 34（42.5%） |
| 完整结果 | 58 |
| 澄清 | 20 |
| 校验失败 | 2 |
| 逐题模型 HTTP 请求 | 245 |

主比较为原生匹配数 / 80，澄清、失败或无完整结果都贡献 0。另列已完成结果的条件准确率。1399 继续保留原生不匹配，不删除或改分。

模型配置保持 qwen3.7-plus、temperature=0、enable_thinking=false；embedding 为 text-embedding-v4/1024，rerank 为 qwen3-rerank。记录服务返回的模型标识；同名服务别名不意味着不可变权重快照。

每题原预算保持：600 秒、总 HTTP 16 次、chat HTTP 10 次、每 SQL 轮最多 3 次生成/校验、SQL 工具调用最多 3 次（含规范值查询）、SQL 30 秒、重试最多 1 次、完整结果 100000 行/64 MiB。独立复评另记 SQL，新增模型调用为 0。

## 3. 服务器运行前核对

从 backend 执行交付检查：

```bash
cd ~/Python_work/askdata_studio_ops_release/backend
python -m scripts.check_m2_public_intent_delivery
```

然后核对当前代码、模型配置及题目清单。该命令加载模型配置但不打印密钥、不连接模型或数据库：

```bash
python - <<'PY'
import json
from pathlib import Path
from evaluation.bird.diagnostic_runner import select_development
from evaluation.bird.intent import policy
from evaluation.bird.manifest import code_binding
from evaluation.bird.model import ModelConfig
from scripts.m2_b_common import digest_file

accepted = json.loads(Path('evaluation/results/m2_public_intent_v3_diagnostics14_server.json').read_bytes())
baseline = json.loads(Path('evaluation/results/m2_c_bird_development80_server.json').read_bytes())
assert digest_file(Path('evaluation/results/m2_c_bird_development80_server.json')) == '7f59478b5d589a49d85027e965e8b3596416ac998df4618c655984841fc8c01d'
assert accepted['code_binding'] == code_binding(), 'Code/dependency/environment changed'
assert accepted['intent_candidate_policy'] == policy(), 'Candidate policy changed'
assert accepted['model_configuration'] == ModelConfig.load(Path('.env')).public(), 'Model configuration changed'
assert accepted['model_configuration'] == baseline['model_configuration']
assert accepted['source_binding'] == baseline['source_binding']
case_list = Path('evaluation/cases/bird_mini_dev/m2_pg_v1/development80.json')
assert digest_file(case_list) == '237b6f09f8b7ee9965f9e18b3ab2195a79b5ad949e55e6d56868a3266df29b10'
cases = select_development(case_list)
assert len(cases) == 80
assert [c['case_id'] for c in cases] == [c['case_id'] for c in baseline['cases']]
print('Ready: unchanged v3 code/model/source, exact development80, baseline 34/80')
PY
```

若断言失败，先核对原因，避免把不同版本结果当作同一候选。实际目标数据和权限仍由 runner 新鲜验证；这里的静态检查不替代实时验证。

## 4. 完整 80 题模型诊断

```bash
python -u -m evaluation.bird.diagnostic_runner \
  --case-list evaluation/cases/bird_mini_dev/m2_pg_v1/development80.json \
  --model-config-file .env \
  --schema-coverage --intent-candidate --save-snapshot \
  --output evaluation/results/m2_public_intent_v3_development80_server.json
```

观察进度应为 1/80 至 80/80。报告仍标记 development_diagnostic_subset、formal_benchmark=false，因为使用的是开发候选 runner；它覆盖完整 development80 不会自动成为正式保留题评测。

run_status=complete 表示流程完成，不等于所有题正确。澄清或校验失败可能是待分析的结果；如果出现来源、预算、隔离或证据不完整导致复评入口拒绝，应保留报告并核对，不能直接跳过验证或放宽评分。

## 5. 独立原生复评

80 题诊断完成后，保持代码和依赖不变：

```bash
candidate_sha=$(sha256sum evaluation/results/m2_public_intent_v3_development80_server.json | cut -d ' ' -f 1)
python -u -m scripts.rescore_m2_intent_candidate \
  --source-report evaluation/results/m2_public_intent_v3_development80_server.json \
  --source-sha256 "$candidate_sha" \
  --output evaluation/results/m2_public_intent_v3_development80_native_server.json
```

复评对每道具有完整预测 SQL 的题执行预测和 Gold，各 1 次，最多 160 次结果查询，0 次新模型请求。未回答题进入 excluded_cases，仍留在 development_subset_case_count=80 的整体比较中。原生比较不增加列名别名、数值容差或 NULL/标签转换。

输出路径存在时使用新文件名，并同步修改后续 source-report 与哈希计算路径；保留所有原始报告。模型诊断至原生复评之间不调整规则或 .env 配置。

## 6. 下载这两份报告

1. `m2_public_intent_v3_development80_server.json`
2. `m2_public_intent_v3_development80_native_server.json`

放到本地 `backend/evaluation/results/` 后进行统一核对。

## 7. 四方面验收

### 新规则误拒绝

逐条核对单位、输出组、排序、粒度等本地拒绝的公开依据及修复结果。拒绝次数本身不是误拒绝次数。对疑似错误阻断，保留拒绝前 SQL，在可信进程做无模型原生复评；参考结果不回传生成模型。

### 原有成功题保持

对原始 34 个成功题逐题列出保持/退化，对最新 14 题的 13 个成功题再单列回归情况。统计新增通过数和丢失通过数；整体净增 = 新增通过 − 原成功题退化。按 8 个数据库各 10 题分别比较。

### 首次生成质量和修复成本

统计首次生成校验通过、PG 分析错误、本地约束拒绝、澄清、重复 SQL 终止、生成次数、HTTP/SQL 调用、模型返回 usage 和 p50/p95 延迟。首次校验通过不等于首次原生正确；原生错误需要单独评判。

共享索引成本与逐题成本分列，避免把索引重新构建差异归因于生成效率。澄清也要核对是否有具体的缺失字段/歧义依据。

### 相对原始基线的提升

与 34/80、20 次澄清和 2 次校验失败做配对比较，并记录 source_binding、模型、预算和冻结评分是否一致。14 题局部改善通过 80 题验证后，再判断可否冻结候选进入后续阶段。holdout30 保持关闭。
