# M2 两题诊断：百分数路径与标题输出

日期：2026-10-18。状态：本地脚本与测试准备；实际 PostgreSQL 诊断等待服务器执行。

## 本轮范围

按已审查的 v2 报告，先完成 0201 与 0586 的无模型诊断。得到服务器原生结果后再修改通用生成规则、补边界测试并重跑同样 14 题。1399 继续记为原生不匹配和参考输出形态差异。

本轮新增两个独立脚本、测试和说明，不修改 Agent、检索、修复、执行器或评分代码。审查脚本位于 `scripts/`，不进入候选的 95 文件代码身份，因此保持已验收 v2 执行环境身份。审查脚本自己的两个文件另行记录 SHA-256。

## 固定输入

| 报告 | SHA-256 |
| --- | --- |
| m2_public_intent_v2_diagnostics14_server.json | 4743a1b3234f358a51684278c093b31baaea26de3bfc3c3b4c110c2863f6ee52 |
| m2_public_intent_v2_native14_server.json | f0170d51cbcef805c13befc590c101678f5277fe6ef50b76dc7c2667500d7c08 |

两份文件按内容哈希验证，可用参数指定其他文件名，但内容必须完全相同。校验文件哈希、来源和当前代码身份后才加载可信 Gold 并连接数据库。重新验证两个数据库的实际权限、元数据及数据版本，不重用旧报告作为当前数据库就绪证明。

## 0201：9 条查询

1. 原始生成 SQL，完整保留字节。
2. 原始冻结 Gold，完整保留字节。
3. 当前 EXISTS 人群上的分子计数和非零分母计数。
4. REAL 分子先乘 100 后除。
5. REAL 分子先除后乘 100。
6. 双精度分子先乘 100 后除。
7. 双精度分子先除后乘 100。
8. NUMERIC 分子先乘 100 后除。
9. NUMERIC 分子保持未缩放比例。

所有变体从已生成的最终 SQL 的 AST 构造，保留当前 EXISTS、关联键、条件、分子定义和分母，不从 Gold 复制 SQL 结构。Gold 仅用于审查进程中的原生比较。SQL 构造保留 PostgreSQL typed division，防止构造库静默添加额外 DOUBLE 转换。

读取原生值、Python 原生类型标签及浮点十六进制表示；不增加 pg_typeof 或其他函数权限，不扩大执行器函数白名单。不同 SQL 类型的具体表达式均写入报告。

**单位约定待确认：**问题要求 percentage，官方 evidence 的 DIVIDE 公式未写乘 100，Gold 则乘了 100。先明确记录这一冲突。后续通用候选应显式记录输出单位、缩放及依据，并区分百分数、0—1 比例、明确公式和冲突场景；不能默默按 Gold 为某题补特殊规则。

当前分数为 `0.3880961092816197`，参考为 `38.80961092816197`。对返回值在 Python 后乘 100 仍差一个浮点最小间距；SQL 实际运算路径需要本轮证据，不能直接宣称修复完成。

## 0586：6 条查询

1. 原始生成 SQL。
2. 原始冻结 Gold。
3. 补 title、保留 ILIKE 和 DISTINCT。
4. 补 title、保留 ILIKE、去掉 DISTINCT。
5. 补 title、改用 LIKE、保留 DISTINCT。
6. 补 title、改用 LIKE、去掉 DISTINCT。

变体保留 users-votes-posts 当前关联和 BountyAmount 条件，仅改变标题投影、大小写操作符或去重；完整报告各组合，以区分影响。

报告另列完整用户/标题元组比较、LIKE/ILIKE 比较、去重前后行数和原生集合比较，以及原预测用户名与参考第一列的诊断比较。最后一项不改变原题评分：单列预测依旧按完整参考列比较。

**通用输出约定待确认：**图和 contract 已有 actor/context 标题组建议，但模型没有投影标题。后续应明确可见的输出组和适用边界；仅用作筛选的上下文字段不能在所有问题中自动变成必选输出列，也不能通过题号或参考答案投影决定规则。

## 预算、隔离和失败记录

- 固定两题、共 15 次结果查询，0 模型请求，不运行 Agent、索引构建或检索。
- 0201 分 3 批、0586 分 2 批，每批最多 3 次 SQL，使用现有 Budget，不提高 Agent 的 3 次 SQL 上限。
- 每题所有批次共享同一开始时间和 600 秒上限；单次 SQL 继续遵循执行器既有 30 秒、结果行数/字节、只读事务和权限限制。
- 这 15 次是独立审查预算，每个查询在报告中都有 SQL、哈希、事件、批次预算和原生结果。它们不并入旧模型预算，也不冒充旧 Agent 执行。
- 执行异常时保留已消耗预算和部分结果，关闭连接池；源 SQL 或 Gold 结果与已验收摘要不一致时拒绝完成验收。
- `run_status=complete` 仅表示诊断计划完成，变体匹配不能替代原预测或提高正式分数。

## 服务器执行

上传 `M2_units_context_probe_sync_20261018.zip` 到项目根目录后：

```bash
cd ~/Python_work/askdata_studio_ops_release
unzip -o M2_units_context_probe_sync_20261018.zip
cd backend
python -m scripts.check_m2_public_intent_delivery
python -m scripts.check_m2_public_intent_delivery \
  --manifest evaluation/m2_units_context_probe_delivery_files_20261018.json
python -m unittest discover -s tests -p 'test_m2_units_context.py' -v
```

既有交付检查仍应通过，因为模型候选代码未修改。第二条检查同时验证新增脚本、测试、说明和已有候选文件，清单为 `evaluation/m2_units_context_probe_delivery_files_20261018.json`。

执行实际两题无模型诊断：

```bash
python -u -m scripts.check_m2_units_context \
  --source-report evaluation/results/m2_public_intent_v2_diagnostics14_server.json \
  --native-report evaluation/results/m2_public_intent_v2_native14_server.json \
  --output evaluation/results/m2_units_context_probe2_server.json
```

无需 `--model-config-file`、模型密钥或新的生成请求。使用既有外部数据和只读账号凭据。若输出存在，改用新文件名，保留全部原始报告。

运行后将 **m2_units_context_probe2_server.json** 下载到本地 `backend/evaluation/results/`。下一步核对各变体及计数，确定通用候选规则，再安排新的 14 题生成和独立原生复评。

1399 本轮不执行、不改 Gold、不做标签或 NULL 归一化，仍保留其原始不匹配与参考形态审查。
