# M2 A 本地数据库包检查记录

检查日期：2026-10-15。证据见 [JSON 报告](results/m2_a_archive_integrity_20261015.json)。本次只读取压缩包和 SQL 文本，没有执行数据库导入或调用模型。

## 已通过的完整性检查

| 项目 | 结果 |
| --- | --- |
| 文件 | `E:\PythonLearn\datasets\bird_mini_dev\downloads\minidev_0703.zip` |
| 文件大小 | 799,944,582 字节，与官方下载响应记录一致 |
| ZIP 目录 | 246 条，包括目录和 macOS 附加条目；名称、大小、压缩大小、CRC 与压缩类型均与此前官方远程目录一致 |
| 全部文件 CRC | 219/219 通过，完整读取累计 3,539,193,972 字节的展开内容 |
| 路径检查 | 未见路径穿越、绝对路径、Windows 重名目标、符号链接或加密文件 |
| PostgreSQL 所需文件 | 79 个文件已计算逐文件 SHA-256；尚未写入解压目录 |

原始包 SHA-256：

```text
aeb211c0e39010bbdae3838bb5e8bd27dc446ed77495b1709f85ccc9bf67f2be
```

官方 SHA-256 尚未提供，本值是本地文件的版本固定证据，不能单独证明发布者身份或没有恶意内容。

## PostgreSQL SQL 文本观察

包内 `minidev/MINIDEV_postgresql/BIRD_dev.sql` 大小为 1,001,882,533 字节，SHA-256 为：

```text
31b1da211849d24a57c9af7636da46a5b82fc8a3ca1542bb3ebd8775e9a31cec
```

完整文本读取发现 75 条建表语句、75 个 COPY 数据块、累计 3,898,114 条 COPY 数据行。这里统计的是源 dump 文本，不代表目标数据库已导入或数据一致性已通过。表在 `public` schema 中，后续需为 11 个逻辑 `db_id` 建立受控授权映射。

COPY 数据区之外的文本模式检查未命中以下内容：psql 元命令、`COPY PROGRAM`、COPY 服务器文件路径、函数/过程或扩展创建、匿名 DO、`SECURITY DEFINER`、已列出的服务器文件/外部连接函数、角色/数据库创建、`ALTER SYSTEM`、数据库删除及触发器创建。完整匹配范围与结果写入 JSON。

发现 99 处 `OWNER TO xiaolongli`。导入脚本应显式审查并映射这些所有权声明，不应依靠创建作者账号来绕过错误。SQL 中其他权限和会话设置还需在受控导入实施时审查。上述模式检查不等同完整语法安全审计，也不替代病毒扫描。

## 首次检查时的安全扫描状态

Windows Defender 状态读取显示 `AMServiceEnabled=false`、`AntivirusEnabled=false`、`RealTimeProtectionEnabled=false`；针对本包尝试不自动修复的自定义扫描失败，退出码 2，HRESULT `0x80004005`。因此没有可记录的 Defender 无威胁结论。

系统注册了腾讯电脑管家，且检查时观察到 `QQPCRTP` 与 `QQPCTray` 进程。该观察不能证明本包已被扫描。已请用户在腾讯电脑管家中对原始 ZIP 进行自定义扫描，并反馈是否发现威胁或扫描失败。

首次 JSON 报告状态为 `integrity_verified_antivirus_pending`，该原始报告继续保留，未把后续扫描结论写回旧证据。

## 用户反馈扫描结果后的后续记录

用户随后明确反馈：“扫描完成，未发现威胁”。本阶段把该结论标记为 `user_reported_no_threats`，产品为腾讯电脑管家、证据类型为用户消息；未独立读取厂商扫描日志，也未把 Windows Defender 的失败改记为通过。

收到反馈后再次计算原始包 SHA-256，与前次完整性检查一致。随后只解压白名单中的 79 个文件，合计 1,002,510,820 字节，保存到：

```text
E:\PythonLearn\datasets\bird_mini_dev\extracted\
```

PostgreSQL SQL 的实际路径为：

```text
E:\PythonLearn\datasets\bird_mini_dev\extracted\minidev\MINIDEV_postgresql\BIRD_dev.sql
```

全部文件的解压字节数和 SHA-256 均与此前记录一致；解压目录中没有额外文件。当前 Hugging Face 500 题文件也重新核对了摘要。新证据见 [本地数据就绪记录](results/m2_a_data_ready_20261015.json)，其中保留原始来源与完整性报告摘要、用户扫描反馈、逐文件位置和 SHA-256。

此阶段仅表示本地资料就绪。下一步冻结开发集、按数据库或模板隔离的保留集、允许的 evidence 与评分协议，然后准备数据库授权映射、受控导入与一致性核验。数据库连接、导入和 Gold 执行尚未开展，模型新增请求数为 0。
