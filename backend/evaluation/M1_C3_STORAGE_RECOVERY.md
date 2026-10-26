# M1 C3：磁盘空间错误诊断与报告写入修复

日期：2026-10-10。

## 当前结论

服务器已打印 41 条 `postgres_typed_rows_verified`，说明每张表的行数和类型化行摘要已匹配。随后出现 `OSError: [Errno 28] No space left on device`，且没有输出后续 24 项检查结果，因此 C3 尚未验收。

原脚本在整个验证期间持有报告文件，结束时写入和关闭文件。如果验证已经失败，报告写入/缓冲刷新再次失败会遮住前面的异常。仅凭现有 traceback 不能确定空间问题是否也影响了 PostgreSQL 临时文件。

PostgreSQL 的磁盘不足错误码为 `53100`，此补丁把它映射为 `disk_full`，保留 SQLSTATE，不记录原始驱动错误文本。参考：[PostgreSQL 错误码](https://www.postgresql.org/docs/16/errcodes-appendix.html)、[磁盘满故障](https://www.postgresql.org/docs/16/disk-full.html)。

## 1. 先检查服务器存储

在服务器执行，只读取状态：

```bash
cd ~/Python_work/askdata_studio_ops_release/backend
df -h . "$HOME" /tmp /var
df -i . "$HOME" /tmp /var
du -xhd1 "$HOME" 2>/dev/null | sort -h
ls -lh evaluation/results/m1_c3_postgres_runtime_server.json
ps -u "$USER" -o pid,args | grep '[p]ostgres'
```

`df -h` 检查空间，`df -i` 检查 inode。`du` 可能需要一些时间，输出仅反映自己有权限读取的目录；它不能完整统计其他用户占用。根据占用结果再决定清理自己确认可丢弃的文件，或让管理员处理共享分区；不要删除数据库目录或 `pg_wal`。保留本次失败文件，可能为空或是不完整的 JSON。

如需确定 PostgreSQL 数据和日志路径，使用自己已有的管理员账号查询：

```bash
"$HOME/.local/askdata/pg16-env/bin/psql" \
  -X -h 127.0.0.1 -p 55432 -U askdata_admin -d postgres \
  -W -v ON_ERROR_STOP=1 -P pager=off \
  -c "SHOW data_directory;" \
  -c "SHOW temp_tablespaces;" \
  -c "SHOW log_directory;" \
  -c "SELECT spcname, pg_tablespace_location(oid) AS location FROM pg_tablespace;"
```

对返回的实际数据/非空 tablespace 路径再执行 `df -h` 和 `df -i`。若需要查看数据库日志，依据实际日志配置找到最近错误，核实是否出现写临时文件失败。不能只把报告改写到 `/tmp` 就认定数据库空间已恢复；`/tmp` 也可能与报告共用分区。

## 2. 应用报告写入补丁

上传项目根目录中的 `M1_C3_报告写入修复同步包_20261010.zip` 到服务器项目根目录，空间恢复后执行：

```bash
cd ~/Python_work/askdata_studio_ops_release
unzip -o M1_C3_报告写入修复同步包_20261010.zip
cd backend
python -m unittest discover -s tests -p 'test_m1_c3_report_storage.py' -v
```

补丁行为：

- 用独占创建的新文件保存 `running` 标记，并 flush/fsync，成功后才进行数据库验证。初始写入失败时不连接数据库。
- 最终报告先写入同目录的独立临时文件，flush/fsync 后替换本次进程创建的标记文件。后续保存失败时保留标记；历史报告仍拒绝覆盖。
- 控制台分别输出验证 `errors` 和 `report_write_error`，空间错误保留 errno，数据库错误保留 SQLSTATE。
- 保存失败时退出码非零、`run_status=failed`；`validation_run_status` 单独记录检查阶段的结果。

这是错误报告修复，不能替代服务器释放空间，也不能保证开始时有空间就能避免运行期间磁盘被其他进程写满。失败后留下的 `running` 标记不是成功验收报告。

本地已执行：8 项报告存储故障测试、31 项连接生命周期测试、26 项运行上下文测试，共 65 项通过。新增测试覆盖初始 fsync 失败、最终 fsync/替换失败、历史文件保护、双异常控制台输出、数据库磁盘错误脱敏和配额错误分类。未在本地连接远程 PostgreSQL。

## 3. 使用新文件名重跑

确认报告目录和数据库使用的文件系统均恢复可用容量后：

```bash
python -u -m scripts.check_m1_c3_postgres_runtime \
  --output evaluation/results/m1_c3_postgres_runtime_server_v2.json
```

若 `_v2.json` 已存在，改用 `_v3.json`，不覆盖。成功应包含 `run_status=complete`、`report_write_status=complete`、`check_pass_count=24`、`errors=[]`、完整 live verification、已关闭连接池，以及 `new_model_request_count=0`。下载完整的新 JSON 后再核实 C3 验收。
