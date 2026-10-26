# M2 v4：完整 development80 生成与独立原生复评

日期：2026-10-18。

## 1. 本轮目的与固定条件

沿用已经核对的 v4 六题候选，扩展到冻结的 80 题完整开发集。检查误拒绝、原成功题保持、首次生成质量及修复成本，再与原始 34/80 和 v3 的 49/80 逐题比较。本轮完成后选择并冻结候选；不因六题中 0201 的退化再追加定向规则。

本次新增的是运行编排脚本，不修改生成、检索、校验、隔离、预算、Gold 或原生评分。96 个候选执行文件保持不变，运行前要求与 v4 六题报告的完整代码、依赖及主机身份一致。

- 已验收生成报告：`m2_public_intent_v4_diagnostics6_server.json`，SHA-256 `20ab65e3b05fb59767a67478ea9d8b5ed426ec9001bb660df9390c2b3023e712`。
- 已验收复评报告：`m2_public_intent_v4_native6_server.json`，SHA-256 `1f7e9f974d678ae118007591b0d2c78d8d8495e4043321077e10627a6895c90a`。
- 固定题集：`evaluation/cases/bird_mini_dev/m2_pg_v1/development80.json`，SHA-256 `237b6f09f8b7ee9965f9e18b3ab2195a79b5ad949e55e6d56868a3266df29b10`。
- 模型公开配置与六题、原始基线一致：qwen3.7-plus、temperature=0、enable_thinking=false；text-embedding-v4/1024；qwen3-rerank。服务端同名模型不代表不可变权重快照，保留实际模型调用记录。
- 每题原有上限保持：600 秒、HTTP 16 次、chat HTTP 10 次、每轮生成/校验最多 3 次、SQL 工具最多 3 次（包含规范值查找）、SQL 30 秒；workers=1。
- 原生复评使用保存的最终 SQL，每个回答最多执行预测 SQL 和原始 Gold 各一次，最多 160 次 SQL，新增模型调用为 0。评分不增加容差、不修改类型、不改变列位置规则。
- 全部 80 题进入分母。未回答、澄清、校验失败不算成功；不能只用已回答题数计算开发集通过率。
- holdout30 保持关闭。本轮是 development diagnostics，不是正式保留题 EX。

v4 六题已生成三个数据库域的索引；其余域可能需要建立对应 v4 索引。索引请求与逐题请求分别统计，以实际 cache_hit/model_usage 为准，不承诺零索引成本。

## 2. 同步包

本地项目根目录文件：`M2_v4_development80_workflow_sync_20261018.zip`。

将它上传到服务器项目根目录 `~/Python_work/askdata_studio_ops_release/`。该包包含编排脚本、测试、本文和独立交付清单；要求之前 v4 同步包已经部署。

```bash
cd ~/Python_work/askdata_studio_ops_release
ls -lh M2_v4_development80_workflow_sync_20261018.zip
unzip -o M2_v4_development80_workflow_sync_20261018.zip
cd backend

python -m scripts.check_m2_public_intent_delivery \
  --manifest evaluation/m2_v4_development80_workflow_delivery_20261018.json

python -m unittest discover -s tests \
  -p 'test_m2_v4_development_workflow.py' -v
```

交付检查应为 complete/errors=[]。若提示文件缺失、代码或依赖变化，先核实同步，不能删除来源检查或修改期望 SHA。

## 3. 无网络调用的运行前检查

在激活原 py311 环境、进入 backend 后执行。它读取 `.env` 验证公开配置但不输出密钥，不读取 PostgreSQL 密码内容、不连接数据库、不调用模型。实时数据、权限和隔离检查仍由原 runner 在实际执行时完成。

```bash
python -u -m scripts.run_m2_v4_development80 \
  --check-only \
  --output "evaluation/results/m2_v4_development80_preflight_$(date -u +%Y%m%dT%H%M%SZ).json"
```

要求 run_status=complete、phase=preflight_only。`live_readiness_verified=false` 符合静态检查范围。目标生成及复评报告路径必须尚不存在；此检查不会创建它们。

## 4. 后台启动一次完整流程

不要同时再手动运行生成或复评命令。脚本会使用当前 Python、同一 v4、相同 `.env`、相同题集和预算；生成完成后进行严格来源及完整性校验，内部计算源报告 SHA，再启动原生复评，无需手动维护 candidate_sha。

```bash
nohup python -u -m scripts.run_m2_v4_development80 \
  --output evaluation/results/m2_public_intent_v4_development80_workflow_server.json \
  > evaluation/results/m2_public_intent_v4_development80_workflow_server.log 2>&1 < /dev/null &
echo "后台进程 PID: $!"
```

默认生成两份主要报告：

1. `evaluation/results/m2_public_intent_v4_development80_server.json`
2. `evaluation/results/m2_public_intent_v4_development80_native_server.json`

第三份 workflow JSON 是阶段状态与证据哈希记录，不是另一份模型评测。它的 `new_model_request_count=null` 表示调用统计以子报告为准。

同一 results-dir 的此工作流有进程锁，防止重复启动同类编排；锁不替代其他手动任务的管理。不要在运行中更新代码、依赖、模型配置或原始证据。

SSH 断线后，nohup 任务通常继续执行。命令返回启动 PID 只表示已启动，不表示运行成功。脚本不自动重试生成，也不跨版本续跑。

## 5. 查看进度与最终状态

```bash
tail -n 40 evaluation/results/m2_public_intent_v4_development80_workflow_server.log
pgrep -af '[p]ython.*(scripts.run_m2_v4_development80|evaluation.bird.diagnostic_runner|scripts.rescore_m2_intent_candidate)'
```

核对三个报告：

```bash
python - <<'PY'
import json
from pathlib import Path

for name in (
    'm2_public_intent_v4_development80_workflow_server.json',
    'm2_public_intent_v4_development80_server.json',
    'm2_public_intent_v4_development80_native_server.json',
):
    p = Path('evaluation/results') / name
    print('\n文件:', name)
    if not p.exists():
        print('尚未创建')
        continue
    try:
        r = json.loads(p.read_bytes())
    except (OSError, ValueError):
        print('暂不可读取，结合日志和进程检查')
        continue
    print('状态:', r.get('run_status'), '阶段:', r.get('phase'))
    print('已保存题数:', len(r.get('cases', [])))
    print('原生比较完成:', r.get('native_comparisons_complete'))
    print('连接池关闭:', r.get('pools_closed'))
    print('错误:', r.get('errors'))
    print('汇总:', r.get('summary'))
PY
```

原 diagnostic_runner 在退出 journal 时才保存完整病例数组；运行期间根报告显示 running、0 题可能正常，以日志的 `[n/80]` 为进度。workflow JSON 在阶段切换时更新。不要仅凭空日志或文件存在判定完成。

最终要求：workflow complete/phase=complete；生成 complete/80 题；复评 complete/native_comparisons_complete=true/pools_closed=true/errors=[]；开发集分母=80。并不要求 80 题全对。

## 6. 中断或失败的处理

先检查后台进程，存在时不要重复启动。任何旧报告保留，选择新输出路径。

如果**生成报告已经 complete 且恰好 80 题，只有复评未完成**，可以使用以下命令只补跑复评，不再调用模型、不读取 `.env`。完整来源、代码和预算记录仍须通过同一原生加载器检查。

```bash
retry_stamp=$(date -u +%Y%m%dT%H%M%SZ)
nohup python -u -m scripts.run_m2_v4_development80 \
  --replay-only \
  --diagnostic-output evaluation/results/m2_public_intent_v4_development80_server.json \
  --native-output "evaluation/results/m2_public_intent_v4_development80_native_retry_${retry_stamp}.json" \
  --output "evaluation/results/m2_public_intent_v4_development80_workflow_retry_${retry_stamp}.json" \
  > "evaluation/results/m2_public_intent_v4_development80_retry_${retry_stamp}.log" 2>&1 < /dev/null &
echo "复评后台 PID: $!"
```

如果生成报告是 running/failed/缺题，不得直接复评。先确认旧进程已退出并核对失败原因，再讨论是否用三个新文件名重跑；当前脚本没有逐题断点续跑，不会自动追加预算或模型生成。不要把历史 v3 报告改标签当作 v4。

## 7. 下载与后续验收

正常完成后下载以下两份到本地 `backend/evaluation/results/`，另保留 workflow JSON 和日志：

- `m2_public_intent_v4_development80_server.json`
- `m2_public_intent_v4_development80_native_server.json`

若使用 retry 文件名，下载实际 complete 的报告并同时提供 workflow JSON。

随后做离线逐题比较：原始 34/80、v3 的 49/80、v4 新结果；分列新增成功与丢失成功、误拒绝证据、首次 SQL/修复成本、共享索引及逐题调用成本。1399 的参考形态问题保留原生失败并单列，0201 的粒度歧义如实记录。不要根据目标答案调整统计。

只有比较完成并选择冻结候选后，才准备受控 holdout30 入口和正式尝试登记，随后进行一次正式保留集评测和 M2 归档。
