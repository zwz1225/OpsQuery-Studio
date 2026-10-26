# M2：三题粒度拒绝的无模型原生诊断

日期：2026-10-18。当前步骤只确认已有约束是否误拒绝，不修改生成策略、题集、Gold或评分规则。

## 1. 固定输入与用途

只接受已经下载审查的两份服务器原始报告，文件路径可显式指定，字节摘要必须一致：

| 报告 | SHA-256 |
| --- | --- |
| `m2_public_intent_v3_development80_server_rerun_v2.json` | `8823926748c359d43ae011e94a1bed8fe5cf592599170c831840d51325ad398b` |
| `m2_public_intent_v3_development80_native_server_rerun_v2.json` | `a6b2cadaff7bf20e47ab210182c05029c98ab61b4adef803a5d9450fd832a551` |

脚本核对完整80题生成/76题复评身份链、4题排除记录、代码与依赖环境、数据/catalog版本、权限和原始SQL捕获。只处理三道开发题，不开放保留题，不通过CLI接收任意SQL。

| 顺序 | 题目 | 原始状态 | 精确执行的SQL | 次数上限 |
| --- | --- | --- | --- | ---: |
| 1 | 0263 | 最终SQL已执行但原生不匹配 | 首次被拒SQL、保存的最终SQL、冻结Gold | 3 |
| 2 | 0273 | 校验失败，无最终结果SQL | 首次被拒SQL、冻结Gold | 2 |
| 3 | 0201 | 最终SQL原生匹配 | 首次被拒SQL、保存的最终SQL、冻结Gold | 3 |

总计最多8条受控SELECT，新增模型请求为0。SQL保持报告中的原始字节，不增加SQL变体。0201作为对照；不预设三题的匹配结果，完成不要求首次SQL匹配或不匹配某种预期。

脚本使用已有BIRD专用凭据 `~/.local/share/askdata/m2_bird_credentials.json`，只请求toxicology的授权runtime和只读角色。运行前重新验证数据/catalog/ACL；模型配置和密钥不需要加载。原生成/检索代码与索引身份保持不变：新增helper和入口放在`scripts/`，不放进绑定全部Python文件的`evaluation/bird/`目录。

## 2. 安全及预算边界

- 首次SQL原业务校验会被离线重建并记录；可信审查执行不会再次用该业务规则阻止这次反事实诊断。
- 来源、只读、函数、字段、数据库角色、事务、超时、行数和负载限制继续由现有执行器执行，不扩展授权表或函数白名单。
- 每题一个零模型Budget、最多3条SQL、共享600秒期限；SQL30秒、连接10秒、锁等待5秒，完整结果最多100000行/64MiB。
- 原生比较保留原来的tuple-set规则，不添加数值容差、结果舍入、列裁剪或类型/标签转换。
- 对0263/0201的最终结果和Gold，重新执行结果的完整诊断必须与原生报告相同，原生比较记录也必须一致；否则保留差异并终止。
- 0273首次SQL从未在原生成阶段执行，明确记录`first_sql_previously_executed=false`；不伪造已有结果或“恢复通过”。
- SQL错误、部分结果、超时、来源或代码变化会使诊断失败；保存已完成查询及预算，在finally关闭连接池。成功/失败输出都保留，不覆盖旧文件。

本脚本是**可信审查入口**，不应被Agent或生成工具导入；首次SQL偶然匹配Gold也不能单独证明其所有业务语义正确。

## 3. 上传与本地/服务器测试

同步包：项目根目录的`M2_grain_diagnostics_sync_20261018.zip`。共5个新文件：

1. `backend/scripts/m2_grain_diagnostics.py`
2. `backend/scripts/check_m2_grain_diagnostics.py`
3. `backend/tests/test_m2_grain_diagnostics.py`
4. `backend/evaluation/M2_GRAIN_DIAGNOSTICS_ACCEPTANCE.md`
5. `backend/evaluation/m2_grain_diagnostics_delivery_files_20261018.json`

先上传压缩包到服务器项目根目录，再解压：

```bash
cd ~/Python_work/askdata_studio_ops_release
ls -lh M2_grain_diagnostics_sync_20261018.zip
unzip -o M2_grain_diagnostics_sync_20261018.zip
cd backend
```

交付清单复用已有只读检查器，核对本次新文件与已冻结v3的全部执行代码：

```bash
python -m scripts.check_m2_public_intent_delivery \
  --manifest evaluation/m2_grain_diagnostics_delivery_files_20261018.json

python -m unittest discover -s tests \
  -p 'test_m2_grain_diagnostics.py' -v
```

专项测试使用模拟执行器和已保存报告，不连接数据库、不调用模型；Windows测试仅在先确认全部96个实际执行文件相同后，模拟捕获时的Linux环境元数据。生产脚本仍严格核对完整环境绑定。测试不是服务器实时执行通过证明。

## 4. 服务器执行命令

保持py311环境、当前代码/依赖和已验证数据不变。确认输出文件不存在；若已经存在，保留它并换新后缀，同时更新日志名。

```bash
ls -l evaluation/results/m2_grain_rejection_diagnostics3_server.json
```

首次执行预期提示不存在。随后启动一次：

```bash
nohup python -u -m scripts.check_m2_grain_diagnostics \
  --source-report evaluation/results/m2_public_intent_v3_development80_server_rerun_v2.json \
  --native-report evaluation/results/m2_public_intent_v3_development80_native_server_rerun_v2.json \
  --output evaluation/results/m2_grain_rejection_diagnostics3_server.json \
  > evaluation/results/m2_grain_rejection_diagnostics3_server.log \
  2>&1 < /dev/null &

echo "后台PID: $!"
```

查看进度：

```bash
tail -n 40 evaluation/results/m2_grain_rejection_diagnostics3_server.log
pgrep -af '[p]ython.*scripts\.check_m2_grain_diagnostics'
```

日志会先提示身份核对、实时数据/catalog/ACL验证，再逐题输出first_match和final_match。主JSON在运行期间可能仍为running占位文件，不是可续跑检查点；不要据此重复启动。

完成后检查：

```bash
python - <<'PY'
import json
from pathlib import Path
p = Path('evaluation/results/m2_grain_rejection_diagnostics3_server.json')
r = json.loads(p.read_bytes())
for key in ('run_status', 'target_data_verified', 'diagnostic_comparisons_complete',
            'pools_closed', 'new_model_request_count', 'errors', 'summary'):
    print(key + ':', r.get(key))
PY
```

成功应为complete、目标验证完成、比较完成、连接池关闭、errors为空，summary三题/8条SQL/0次模型。first_matches_reference_case_ids不预设数量。任何failed报告保留并先定位原因，不放宽来源校验。

## 5. 下载后核对

只需下载新的`m2_grain_rejection_diagnostics3_server.json`到本地`backend/evaluation/results/`。接下来核对：

1. 两份源报告/执行代码/audit代码摘要及toxicology来源身份。
2. 首次SQL与原拒绝记录的字节、位置顺序、原业务理由重建。
3. 首次/最终/Gold完整原生结果及比较，0201与0263的差异。
4. 0273公开evidence内部cl/pb冲突及粒度假设，判断哪些拒绝不适用。
5. 8条SQL预算、0模型、结果完整性和资源关闭。

本轮仍保持development80得分49/80。无模型反事实成功属于诊断证据，不回填Agent成绩；根据证据决定下一轮有限规则修正，再做定向验证。
