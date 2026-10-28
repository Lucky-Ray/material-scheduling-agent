# 离线运行证据索引

所有现有 Trace 的 mode 都是 mock。它们由本目录 generate.py 实际运行并断言产生，不是手工编写的模型日志。重新生成：在项目根目录运行 `python examples/generate.py`。

## 文件约定

- `<场景>.input.json`：业务输入。
- `<场景>.catalog.json`：本次使用的完整合成数据快照。
- `<场景>.trace.json`：实际业务输出和完整工具记录。
- `duplicate.first.trace.json`：重复场景第一次执行结果；duplicate.trace.json 为第二次。
- `scenario-results.json`：场景预期、实际状态、草稿数量、工具路径和断言结果。
- `test-results.txt`：unittest 的实际输出。
- `generate-results.txt`：场景生成器的实际输出。
- `verification-summary.json`：本轮验证环境、数量和退出码。

## 场景列表

| 场景名 | 检查内容 | 预期 |
| --- | --- | --- |
| normal | 原时间审核并保存 | completed |
| conflict | 柔性时间遇到占用后换时段 | needs_confirmation，pending 草稿 |
| missing | 找不到素材 | blocked |
| missing_metadata | 缺少 rights | blocked |
| risk | 风险规则命中 | blocked |
| save_failure | 保存故障 | failed |
| hard_conflict | 硬时间冲突 | needs_confirmation，无草稿 |
| duplicate | 相同请求执行两次 | 相同 ID，只一条草稿 |
| no_slots | 无可用候选 | blocked |
| changed_occupied | 清除占用后的同一冲突输入 | completed，原时间草稿 |
| changed_rule | M01 新增风险标签 | blocked |
| step_limit | 决策上限为 1 | incomplete |

## 单个 CLI 复现

```powershell
python src/agent.py --input examples/normal.input.json --mode mock --db :memory:
python src/agent.py --input examples/conflict.input.json --mode mock --db :memory:
python src/agent.py --input examples/save_failure.input.json --mode mock --db :memory: --fail-save
python src/agent.py --input examples/normal.input.json --mode mock --db :memory: --max-steps 1
```

变体 catalog 的重现以 generate.py 为准；CLI 当前固定读取 data/catalog.json，不能直接用 --input 切换规则或占用配置。重复场景需相同数据库运行两次，或使用生成器。

## 真实模型材料

当前没有 live Trace。真实运行后新增 `live-normal.trace.json`、`live-conflict.trace.json` 等，保留实际 mode=live，补充模型名、非敏感配置、日期和人工复核结论；不要把本目录的 mock 标记改成 live。
