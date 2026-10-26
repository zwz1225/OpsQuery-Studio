# M3主项目实际启用改动审计

审计日期：2026-10-26。方式：本地Python源码AST、入口调用及下载报告核对；没有导入app、读取.env/密钥、启动服务或连接服务器。

## 运营Web入口

当前调用关系为 `app/main.py → app/api/routes.py → AskDataService → QueryWorkflow → SingleDatabaseAgent`，仍使用运营runtime、`app/retrieval`、应用SQL校验和 `app/model_client.py`。

静态扫描 `backend/app` 的全部Python文件，没有发现对 `evaluation.bird` 或M3控制器的导入。`app/config.py` 中声明默认值为 `DATA_BACKEND=duckdb`、`DATA_SOURCE_ID=short_video_ops_duckdb`，没有新增M3候选开关。配置可以被环境/.env覆盖，本审计没有读取私密配置，不能据此断言远程服务器当前使用何种后端。

因此当前运营API没有自动启用E01～E07的BIRD语义候选。`app/model_client.py` 仍使用自身urllib调用路径，未接入BIRD专用process DNS；BIRD预算、进程隔离和提示不会因模块存在而自动覆盖运营服务。

## BIRD通用入口与可选开发入口

| 入口/组件 | 实际状态 | 依据 |
| --- | --- | --- |
| `evaluation/run_bird_benchmark.py` | 转入独立 `evaluation.bird.runner`；普通Gold/live请求不附加M3效果开关 | runner请求构造和AST字典字段审计 |
| `evaluation/bird/diagnostic_runner.py` | schema覆盖、intent、输出契约、条件关系、关系输出、类别人口、语义规划均需显式CLI启用 | `store_true`，默认False |
| `evaluation/bird/case_worker.py` | 各feature从request取值，缺省False；语义规划/输出契约限diagnostic+intent，条件关系另检查依赖 | 请求默认值和开发模式拒绝逻辑 |
| E01输出契约 | 存在可选开发接入，未默认启用 | output_enabled分支 |
| E02条件/关系补齐 | 存在可选开发接入，未默认启用 | condition_relations分支 |
| E03关系输出/候选关系 | 存在可选开发接入；来源候选不等于数据库声明外键 | relation_output及reviewed_relations元数据 |
| E04标量计数模块 | 本地有文件；当前case_worker没有导入/调用 | 历史隔离包内的接入不能视作当前worker能力 |
| E05端点提示、E06端点校验 | 本地有文件；当前case_worker没有导入/调用 | endpoint_scope/endpoint_validation仅相互引用或供审查脚本使用 |
| E07语义规划v2 | 开发入口存在，默认False；仅显式语义规划时进入Agent提示 | semantic_planning分支和policy v2 |

这里的intent/coverage也包含M2已建立的机制，不能把它们全部归为M3新增。冻结M2 holdout worker明确启用M2 v4的schema覆盖和intent；未启用M3语义规划、类别人口或输出契约。M2控制器要求完全一致的producer/依赖/host绑定，并拒绝已有登记的重复尝试。当前源码已变更，不能直接拿当前树冒充M2冻结版本复跑。

E04/E05/E06历史隔离实验包包含当时专门接入的worker，相关报告有效；当前通用源码没有接入这些分支并不推翻历史实验。反过来，保留模块文件也不等于当前产品或普通CLI会执行它们。

## 已实际生效的连接层例外

`evaluation/bird/model.py` 的模型HTTP调用已经统一转入 `process_dns.open_url`，属于当前BIRD模型客户端的实际连接行为，未由M3效果开关控制。

- resolver为 `114.114.114.114`，调用 `/usr/bin/dig`，要求版本 `9.18.39-0ubuntu0.22.04.7-Ubuntu`。
- 保留TLS证书/主机名校验，不修改系统DNS或全局socket；环境代理不被继承。
- 配对目录有 `m3_context.json` 时，核对workspace的 `transport_dependency_lock.json` 和bundle身份。
- 非配对调用没有该执行锁时仍检查本机dig身份，继续使用显式DNS；并不会自动退回原系统解析路径。
- 多轮服务器配对报告证明了当前环境下的可用性，不能由此宣称所有网络/操作系统都兼容。dig版本或网络变化会导致前置失败，需要作为可移植性遗留项处理。

本层作为BIRD研究运行支持保留，未迁移进运营app，也不计作问数准确率候选已推广。准备校验使用冻结包内提示字面量的修复属于控制器工具改进，仍不改变业务语义评分。

## 处置与验证边界

本轮没有修改业务开关、生产配置或默认调用链，也没有将未通过候选自动接入运营服务。保留可选开发模块与冻结包，产品接纳数量为0。没有必要为了本地文档收尾重新运行服务器live或重复M2 holdout。

审计机器记录包含上述关键源码哈希、开关所在行、普通runner请求键、M2冻结worker键和模块导入结果，见 [收尾审计v2](results/m3_closeout_audit_local_20261026_v2.json)。这是当前本地源码的静态审计；服务器部署版本、进程环境、真实HTTP行为、并发及生产性能未在本轮重新验证。
