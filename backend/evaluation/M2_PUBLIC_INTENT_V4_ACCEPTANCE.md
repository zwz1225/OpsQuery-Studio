# M2 v4：粒度、evidence冲突与精度的一轮有限修正

日期：2026-10-18。基于v3完整开发80题及三题首次SQL原生诊断，先修正规则适用范围，再生成固定6题并独立原生复评。原始协议、Gold、80题/30题划分和预算不变，v3的49/80保持原记录。

## 修改范围

仅改变三个执行模块：

- `evaluation/bird/relationships.py`：识别COUNT主键仍可提出粒度候选，但只有明确COUNT(DISTINCT)或绑定该实体的unique/distinct/each ... once请求才进行硬拒绝。单纯主键和一对多关联记录为advisory，显式关联记录权重予以保留。
- `evaluation/bird/intent.py`：候选版本升为`bird_public_intent_candidate_v4`；公开条件标注definition、population_filter、numerator_condition、denominator_condition、aggregate_condition及原文位置。相同字段的冲突值单独记录，不升级为强制合取；明确分子/分母不同值的合法比值保留。重复的同字段同值条件合并。
- `evaluation/bird/units_output.py`：从公开文本提取0—15位明确小数要求，记录原文依据；检查简单单数值输出的最终ROUND或NUMERIC固定scale。缺少或错误位数给出`requested_decimal_precision`反馈。复杂输出归属、冲突精度、显式不舍入及不支持位数保守处理。

不修改权限、来源SQL策略、驱动/执行器、原生EX、预算、传输重试或Agent/评分器隔离。没有题号分支，没有参考SQL/结果进入生成规则，不自动重写模型SQL或返回结果。

粒度约束的有效性与原生参考结果必须分开报告：0201和0263公开公式均未明确DISTINCT，v4将两者都作为粒度不明确的提示，不能保证0201首次结果保持正确。保留0201作为正向回归对照；六题不要求预设全通过，也不能把模型未回答题从分母剔除。

## 历史测试与版本边界

调整了四份既有测试以表达新边界：旧粒度测试的硬拒绝正例现在明确要求unique；历史v2/v3报告仍按原始字节校验，测试只模拟相应producer环境和policy，同时核对执行/权限/评分文件未改变。历史三题生产审查入口在v4下仍应拒绝旧代码绑定，不开放跨版本续跑。

新增`tests/test_m2_intent_v4.py`覆盖正反例及六题已有SQL的离线校验。离线已有SQL校验不代表新模型结果或EX得分。完整M2回归的实际数量及结果见本地准备报告。

## 固定验证题

清单：[m2_limited_fix6.json](cases/bird_mini_dev/m2_limited_fix6.json)。六题全部来自冻结development80，Gold在原评分器中，未新增或修改题目正文。

| 题目 | 验证内容 |
| --- | --- |
| 0201 | 粒度提示放宽后的原有效修复对照 |
| 0263 | 模糊粒度不再强制去重 |
| 0273 | cl/pb冲突记录与无依据条件移除 |
| 0226 | 明确五位小数的SQL实现 |
| 0368 | 百分数单位、数值路径保持 |
| 0586 | 已有参与者/上下文输出组保持 |

## 1. 上传同步包并解压

上传项目根目录的`M2_public_intent_v4_sync_20261018.zip`到服务器项目根目录，再执行：

```bash
cd ~/Python_work/askdata_studio_ops_release
ls -lh M2_public_intent_v4_sync_20261018.zip
unzip -o M2_public_intent_v4_sync_20261018.zip
cd backend
```

核对本次清单，不使用旧v3交付清单：

```bash
python -m scripts.check_m2_public_intent_delivery \
  --manifest evaluation/m2_public_intent_v4_delivery_files_20261018.json

python -m unittest discover -s tests -p 'test_m2_intent_v4.py' -v
```

如需执行与本地相同的完整M2回归：

```bash
python -m unittest discover -s tests -p 'test_m2*.py' -q
```

当前模型、API配置、BIRD专用凭据及数据库不需要修改。文件或版本检查不通过时先定位原因；不能修改既有报告的code_binding或跳过来源检查。

## 2. 后台运行六题生成

以下输出名首次应不存在，已存在则保留并改新后缀；不要重复启动同名任务。

```bash
nohup python -u -m evaluation.bird.diagnostic_runner \
  --case-list evaluation/cases/bird_mini_dev/m2_limited_fix6.json \
  --model-config-file .env \
  --schema-coverage --intent-candidate --save-snapshot \
  --output evaluation/results/m2_public_intent_v4_diagnostics6_server.json \
  > evaluation/results/m2_public_intent_v4_diagnostics6_server.log \
  2>&1 < /dev/null &

echo "生成后台PID: $!"
```

查看日志：

```bash
tail -n 40 evaluation/results/m2_public_intent_v4_diagnostics6_server.log
pgrep -af '[p]ython.*evaluation\.bird\.diagnostic_runner'
```

本次3个来源的索引因代码身份变化会使用新目录，旧索引保留；若缓存不存在，将发生共享embedding调用，单独记账。不是0模型运行；每题模型、SQL及600秒预算仍保持原上限。

生成完成后检查：

```bash
python - <<'PY'
import json
from pathlib import Path
r = json.loads(Path('evaluation/results/m2_public_intent_v4_diagnostics6_server.json').read_bytes())
print('状态:', r.get('run_status'))
print('题数:', len(r.get('cases', [])))
print('策略:', (r.get('intent_candidate_policy') or {}).get('policy_id'))
print('连接池关闭:', r.get('preparation_pools_closed'))
print('错误:', r.get('errors'))
print('汇总:', r.get('summary'))
PY
```

预期complete、6题、v4策略、准备连接池关闭、顶层errors为空。题目可能澄清或校验失败，仍保留记录；不能因为流程complete就认为六题全部正确。

## 3. 生成完成后再运行独立原生复评

维持同一代码、依赖与环境；不要对旧v3报告使用v4复评入口。

```bash
candidate_sha=$(sha256sum \
  evaluation/results/m2_public_intent_v4_diagnostics6_server.json \
  | cut -d ' ' -f 1)

nohup python -u -m scripts.rescore_m2_intent_candidate \
  --source-report evaluation/results/m2_public_intent_v4_diagnostics6_server.json \
  --source-sha256 "$candidate_sha" \
  --output evaluation/results/m2_public_intent_v4_native6_server.json \
  > evaluation/results/m2_public_intent_v4_native6_server.log \
  2>&1 < /dev/null &

echo "复评后台PID: $!"
```

复评最多执行12条结果SQL，新增模型请求0次；未回答题仍留在六题分母。查看状态：

```bash
tail -n 40 evaluation/results/m2_public_intent_v4_native6_server.log

python - <<'PY'
import json
from pathlib import Path
r = json.loads(Path('evaluation/results/m2_public_intent_v4_native6_server.json').read_bytes())
for key in ('run_status', 'native_comparisons_complete', 'pools_closed', 'errors', 'summary'):
    print(key + ':', r.get(key))
PY
```

如果生成尚未完成，主JSON可能只有running占位信息，不能用于复评。使用日志确认进度；复评拒绝来源时保留失败报告，核对后换新输出路径。

## 4. 下载与核对

下载至本地`backend/evaluation/results/`：

1. `m2_public_intent_v4_diagnostics6_server.json`
2. `m2_public_intent_v4_native6_server.json`

检查来源/版本、evidence冲突是否送达、粒度mode与SQL选择、0226精度反馈及有效修改、0368/0586保持、0201可能退化、模型及新索引成本、复评完整性与连接池关闭。只有这次定向证据核对后，再决定最终候选及完整80题运行。M2不以清零所有错误为结束条件。
