# M2 v4 冻结候选与一次正式 holdout30 评测

日期：2026-10-19（Asia/Shanghai）。本轮只做候选冻结和保留集评测，不再依据 development80 追加规则。

## 1. 已冻结的内容

候选文件：`evaluation/candidates/m2_v4_holdout30_candidate_20261019.json`。

其中固定：

- 已验收 v4 的96个执行文件及完整服务器 Python、依赖、内核、seccomp 身份。
- qwen3.7-plus、temperature=0、thinking=false、text-embedding-v4/1024、qwen3-rerank，以及公开模型端点；不保存模型或数据库密码。
- 已验收来源、数据库域账号、授权范围、数据/catalog版本、协议11个文件的哈希。
- v4 Schema覆盖、意图约束、修复策略；固定holdout30题集、原始英文问题及官方evidence。
- 固定30题分母、原生tuple-set比较、600秒整题时间、16次总模型HTTP/10次chat、原SQL工具预算及结果上限。
- 新增控制器文件的哈希及评分适配方式。
- 作为选型依据的development80两份报告哈希：50/80，不将其当作保留集成绩。

共享索引费用单列；不承诺保留域新建索引请求为0。模型别名不保证远端权重不可变，保留服务实际返回模型标识与usage。

## 2. 评分适配为何单独实现

现有case_worker将v4开关限制在diagnostic模式。为保持96个已验收执行文件的字节不变，本次增加独立可信入口：

1. 只向原worker传入原公开输入、授权receipt、索引和模型配置，使用原diagnostic生成路径及相同v4开关。
2. 被动观察原数据库调用，保留最后一次完整预测结果的原生Python对象，不修改SQL、不重复执行预测SQL。
3. Agent退出且生成runtime关闭后，可信评分侧以同一账号/来源receipt读取Gold。
4. 评分继续使用原题Budget的剩余时间；外层进程在600秒终止整题，不额外分配600秒。
5. 对完整原生值进行冻结tuple-set比较，完成后才写JSON诊断。Gold不会进入模型输入或修复反馈。

Gold不是生成侧SQL工具调用，单独记录，与原live worker的预算口径一致。澄清、SQL错误、超时、超限均保留在30题分母中。强制终止后无法确认的调用量记未知，不填0。

专项测试包含原worker和真实Agent应答循环的一致性比较：提示词、修复轨迹、最终SQL、预算相同，新路径只在Agent退出后追加Gold查询。

## 3. 同步到服务器

将本地项目根目录中的`M2_v4_holdout30_frozen_sync_20261019.zip`上传到服务器：

`~/Python_work/askdata_studio_ops_release/`

它依赖之前部署的v4及development80工作流文件，包内不包含.env、数据库密码、题库或数据库数据。

```bash
cd ~/Python_work/askdata_studio_ops_release
ls -lh M2_v4_holdout30_frozen_sync_20261019.zip
unzip -o M2_v4_holdout30_frozen_sync_20261019.zip
cd backend

python -m scripts.check_m2_public_intent_delivery \
  --manifest evaluation/m2_v4_holdout30_delivery_20261019.json

python -m unittest discover -s tests \
  -p 'test_m2_holdout_control.py' -v
```

要求交付检查complete/errors=[]、27项专项测试通过。测试使用临时登记目录，不占用正式尝试。

## 4. 只做静态预检

```bash
python -u -m scripts.run_m2_holdout30 \
  --check-only \
  --output "evaluation/results/m2_holdout30_preflight_$(date -u +%Y%m%dT%H%M%SZ).json"
```

要求：`run_status=complete`、`phase=static_preflight_only`、`attempt_registered=false`。

此步骤读取.env检查公开配置，不输出密钥、不连接数据库、不调用模型、不占用正式尝试。`live_readiness_verified=false`符合范围。若主机/依赖/代码哈希不一致，先核实原因，不修改期望哈希绕过检查。

## 5. 后台启动一次正式保留评测

```bash
nohup python -u -m scripts.run_m2_holdout30 \
  --execute \
  --output evaluation/results/m2_v4_holdout30_server.json \
  > evaluation/results/m2_v4_holdout30_server.log 2>&1 < /dev/null &
echo "后台 PID: $!"
```

执行顺序：

1. 静态身份检查通过。
2. 独占登记尝试，持久保存reserved事件。
3. 重新执行隔离、预算及硬超时探针。
4. 对三个保留域验证实时结构、ACL、全量类型化数据和内容guard。
5. 可信侧重新执行全部30条原始Gold就绪检查，全部就绪后才建立索引及启动Agent。
6. 顺序生成并评分30题；每题开始、完整结果文件及保存哈希分别登记。
7. 按全部30题汇总主EX，保存snapshot及完成事件。

SSH断线后nohup任务通常继续。后台PID只表示启动，不表示成功。

### 唯一正式尝试与中断

登记的固定位置为：

`backend/evaluation/results/holdout_attempts/m2_bird_pg_v1/<candidate_id>/`

- 同一候选只接受一次登记。即使进程在登记后、第一题之前失败，也保留该次尝试。
- 目录创建采用独占操作；进程被杀后目录及已写事件仍存在。空的预留目录也不能视为未运行。
- 事件文件只新增、带前一事件文件哈希；逐题结果和Gold就绪记录独立保存。
- 事件完成记录绑定最终报告除journal的finished_at以外的内容摘要。
- 不提供自动重试、逐题续跑、修改ledger目录或重置尝试参数。
- 不要删除、改名或清空登记目录来重复运行。若启动后失败，保留报告、日志、登记材料，先核对原因；后续任何保留题复用必须明确披露，不再声称未参与调参。

该登记是项目内文件约束，不是外部不可篡改服务。删除工作区或人工修改登记会破坏审计链，必须连同其余材料完整归档。

## 6. 查看进度

```bash
tail -n 40 evaluation/results/m2_v4_holdout30_server.log

pgrep -af '[p]ython.*(scripts.run_m2_holdout30|scripts.m2_holdout_worker|evaluation.bird.case_worker)'

python -m scripts.run_m2_holdout30 --status
```

日志先显示Gold readiness `[1/30]`至`[30/30]`，随后显示正式生成`[1/30]`至`[30/30]`。Gold就绪阶段没有模型调用。

根报告在每题后原子更新，能看到当前phase和已保存题数：

```bash
python - <<'PY'
import json
from pathlib import Path
p = Path('evaluation/results/m2_v4_holdout30_server.json')
if not p.exists():
    print('报告尚未创建；先检查日志与进程')
else:
    try:
        r = json.loads(p.read_bytes())
        for key in ('run_status', 'phase', 'attempt_id', 'candidate_id',
                    'fresh_gold30_ready', 'preparation_pools_closed', 'primary_ex', 'errors'):
            print(key, ':', r.get(key))
        print('已保存正式题数:', len(r.get('cases', [])))
        print('汇总:', r.get('summary'))
        print('登记目录:', r.get('attempt_ledger'))
    except (OSError, ValueError):
        print('暂不可读取，结合日志和进程检查')
PY
```

若failed或有来源/预算/隔离异常，不要重跑命令。将实际错误、根报告与登记材料下载后审查。正常运行中的static check会提示已有登记，这不是重跑授权。

## 7. 完成后下载哪些文件

1. `evaluation/results/m2_v4_holdout30_server.json`
2. `evaluation/results/m2_v4_holdout30_server.log`
3. `evaluation/results/holdout_attempts/m2_bird_pg_v1/`整个目录，保持层级；包含事件、30份Gold就绪记录及30份病例文件。

Windows本地都放在相同的`backend/evaluation/results/`层级。snapshot保留在服务器，并按最终归档需要一并下载。

登记目录文件较多，正常完成后也可以用下面的命令打成一个证据包。它先核对登记链和最终报告的绑定，再打包主报告、日志、snapshot及整个登记目录；不包含.env或凭据文件。

```bash
python - <<'PY'
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from scripts.m2_b_common import digest_file, digest_json
from scripts.m2_holdout_control import LEDGER_ROOT, verify_ledger

root = Path('evaluation/results').resolve()
main = root / 'm2_v4_holdout30_server.json'
r = json.loads(main.read_bytes())
assert r['run_status'] == 'complete' and len(r['cases']) == 30
ledger = Path(r['attempt_ledger']).resolve()
assert ledger.is_relative_to(LEDGER_ROOT.resolve())
state = verify_ledger(ledger)
assert state['last_event'] == 'completed' and state['attempt_id'] == r['attempt_id']
last = json.loads(sorted(ledger.glob('[0-9][0-9][0-9][0-9]_*.json'))[-1].read_bytes())
assert last['report_content_sha256'] == digest_json({k: v for k, v in r.items() if k != 'finished_at'})
snapshot = Path(r['snapshot']['path']).resolve()
assert snapshot.is_relative_to(root) and digest_file(snapshot) == r['snapshot']['sha256']
files = [main, root/'m2_v4_holdout30_server.log', snapshot]
files += sorted(p for p in ledger.rglob('*') if p.is_file())
out = root/'m2_v4_holdout30_evidence_server.zip'
with ZipFile(out, 'x', compression=ZIP_DEFLATED) as z:
    for p in files:
        assert not p.is_symlink() and p.resolve().is_relative_to(root)
        z.write(p, str(p.relative_to(root)))
print('证据包:', out)
print('SHA-256:', digest_file(out))
PY
```

下载`m2_v4_holdout30_server.json`及`m2_v4_holdout30_evidence_server.zip`；后者解压到本地`backend/evaluation/results/`保持原层级。如果失败，先保留并下载现有材料，不使用要求complete的打包命令。

主报告应为complete、30题、分母30，登记最后事件completed。运行完成不等于M2验收通过；还需逐题核对来源、模型、预算、隔离、原生评分及所有失败/中断记录。

## 8. M2最终验收与遗留项

见`evaluation/M2_FINAL_ACCEPTANCE_PENDING_HOLDOUT.md`。当前没有holdout结果，不能填写通过率或宣称M2全部完成。报告下载后，再将真实正式结果和逐题失败分类填入最终验收记录；development80的30个已知失败保留为开发遗留，不能与holdout合成一个百分比。
