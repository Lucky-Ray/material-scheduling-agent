# 03 效果验证与限制

## 1. 评估结论与证据等级

当前已执行两类离线验证：可执行单元测试，以及通过示例生成器运行的场景断言。两类都使用 MockModel 或测试替身，不涉及真实远端模型。本报告不能据此给出真实模型决策正确率、审核准确率或生产可用性结论。

真实模型客户端已实现，但当前未配置 MODEL_BASE_URL、MODEL_API_KEY、MODEL_NAME 的完整运行环境，未发起真实模型调用。因此题目要求的“模型观察工具结果后调整下一步”尚缺真实模型运行证据，不标记为完全验收通过。

## 2. 可复制命令

在项目根目录执行：

```powershell
python -m unittest discover -s tests -v
python examples/generate.py
python src/agent.py --input examples/conflict.input.json --mode mock --db :memory:
```

- 单元测试实际输出保存在 `examples/test-results.txt`。
- 场景生成实际输出保存在 `examples/generate-results.txt`。
- 机器可读断言结果保存在 `examples/scenario-results.json`。
- 每个场景分别保存 input、catalog 和 trace；目录变体不会偷偷修改全局资料。

`examples/generate.py` 内置场景断言，断言不符即退出失败。仅运行 unittest 不会刷新示例文件；仅阅读示例也不代表本次已执行测试。

## 3. 单元测试覆盖

| 测试 | 测试预期 | 关键断言 |
| --- | --- | --- |
| test_normal_and_duplicate | 首次完成、再次重放 | 相同 ID、duplicate=true、数据库一条 |
| test_flexible_conflict | 柔性冲突选择替代 | 19 点、pending、未发布 |
| test_hard_conflict | 硬冲突不修改 | needs_confirmation，无草稿 |
| test_missing_and_risk | 素材缺失、风险、缺版权阻断 | UNKNOWN / M02 / M03 均 blocked，数据库零条 |
| test_missing_time | 缺请求时间不保存 | blocked |
| test_save_failure | 保存故障如实失败 | failed、ok=false |
| test_tools_enforce_boundaries | 工具独立守住约束 | 硬时间替代被拒、不同素材竞争同槽被拒 |
| test_limit_and_false_success | 超限与虚报成功 | incomplete；没有保存证据不能 completed |
| test_prerequisites | 不允许模型直接越过前置观察 | prerequisites_not_observed |

以上测试验证了当前离线实现的业务边界。竞争同槽测试是顺序重查，不是并发压力测试，不能表述为已完成高并发验证。

## 4. 场景验收矩阵

| 场景 | 输入或故障设置 | 预期 / 实际 | 数据库条数 |
| --- | --- | --- | --- |
| normal | M01、19 点、硬时间 | completed / completed | 1 |
| conflict | M01、18 点被占、柔性时间 | needs_confirmation / needs_confirmation，19 点 pending | 1 |
| missing | UNKNOWN | blocked / blocked | 0 |
| missing_metadata | M03 缺 rights | blocked / blocked | 0 |
| risk | M02 命中规则 | blocked / blocked | 0 |
| save_failure | 保存故障注入 | failed / failed | 0 |
| hard_conflict | 18 点被占、硬时间 | needs_confirmation / needs_confirmation，无草稿 | 0 |
| duplicate | 同请求连续执行两次 | completed / completed，重放相同 ID | 1 |
| no_slots | 所有时段被占、柔性时间 | blocked / blocked | 0 |
| changed_occupied | 与 conflict 相同请求，清空占用 | completed / completed，18 点原时段草稿 | 1 |
| changed_rule | M01 新增风险标签 | blocked / blocked | 0 |
| step_limit | 只允许一次决策 | incomplete / incomplete | 0 |

实际结果应与 scenario-results.json 一致。发生代码或资料更改后需要重新运行，不能沿用旧结论。

## 5. 至少两条路径的逐步解释

### 路径 A：正常完成

输入 `normal.input.json`。read_material 返回 M01；check_rules 返回 ok=true；query_slots 显示 19 点可用；模型模拟器选择 save_draft(19 点)，保存工具返回 ok=true。下一次决策结束，最终 completed，published=false。

核对：草稿 slot 等于 requested_slot；confirmation=not_required；Trace 中有实际保存证据，不把“准备保存”写成“保存成功”。

### 路径 B：冲突后调整

输入 `conflict.input.json`。请求 18 点且 hard_time=false。前两步正常，query_slots 返回 requested_available=false，available 包含 19、20 点。下一步改选 19 点保存；草稿 confirmation=pending，最终 needs_confirmation。

核对：18 点没有被覆盖，19 点来自工具返回，不是模型臆造；替代时间没有伪称已经获批或发布。

### 路径 C：保存失败

使用 `save_failure.input.json`，生成器设置 fail_save=True；CLI 重现时需加 `--fail-save`。前置步骤成功后保存返回 injected_storage_failure，模拟器结束为 failed，数据库零条。

核对：资料和时段检查成功不能替代保存成功；故障结果保留在 Trace 中。

## 6. 结果扰动验证

对比 conflict 与 changed_occupied：请求一致，只把已占用列表从 18 点改为空，后续动作从“保存 19 点 pending”变成“保存 18 点原时段”。对比 normal 与 changed_rule：请求一致，只给 M01 增加风险标签，后续动作从“查时段并保存”变成“审核后阻断”。

这些扰动验证模拟流程确实依赖工具结果；它们仍然不是对真实模型的扰动验证。各场景 `.catalog.json` 保存实际数据快照，`generate.py` 是重现这些变体的入口，CLI 现可用 --catalog 指定快照，直接复现不同工具结果。

## 7. 真实模型验收操作

1. 按 README 配置三个环境变量。记录提供商、模型名、测试日期及非敏感版本信息。
2. 使用两个全新数据库分别跑 normal 和 conflict，保存 live-normal.trace.json 与 live-conflict.trace.json。
3. 检查每条 Trace：是否先获得素材、规则、时段；下一步是否依据可用性改变；是否引用真实工具返回；是否在上限内结束。
4. 对 conflict 应看到替代 slot 来自 available、confirmation=pending；对硬时间冲突应停止等待确认，不能替代。
5. 真实模型还应执行保存失败、缺信息、风险场景；失败不改写为成功。
6. 对占用和规则进行一次实际资料扰动后再次运行，将变动前后数据快照与模型动作一起保存。临时修改全局 catalog 后要恢复，不能覆盖原始证据。
7. 将实际观察补入本报告；若不符合预期，保留失败 Trace，修复后同时保存修复前后记录。

真人核验记录：**尚未执行，不填写虚构结果。**

## 8. 本轮修复与已知限制

本轮增加 tests/test_hardening.py 的 10 项测试：模型换候选时段仍请求级防重、规则变化重查、request_id 不能挪用、重放不能绕过硬约束、错误输入与动作协议、聚合审核结果、执行上限保留保存事实、CLI 初始化错误 JSON 和非零退出、catalog 覆盖、旧数据库迁移。与原 9 项合计 19 项，本地全部通过。

| 项目 | 本轮处理 | 仍存边界 |
| --- | --- | --- |
| 请求级幂等 | 显式 request_id 或素材+原时间映射唯一草稿 | 想改变业务意图需新 request_id；不实现草稿编辑 |
| 规则变化重放 | 返回旧结果前重查当前规则 | 不自动撤回已存在历史草稿 |
| 协议校验 | 校验对象、布尔、枚举、白名单和 slot 类型 | 未做完整目录 Schema、自然语言时间解析或模型格式自修复 |
| 结果聚合 | material_result 输出审核、风险、缺失、确认和保存状态 | 尚无交互界面 |
| 状态与副作用 | failed / incomplete 也保留成功 draft | 执行状态仍不等同于业务保存状态，调用方需分别判断 |
| CLI 错误 | 配置、文件、数据库、输出错误统一 JSON；失败退出 1 | 不自动恢复，输出文件写入失败只能打印到 stdout |
| 真实模型 | 接入和操作说明保留 | 用户本轮选择暂不运行，未完成真实决策证明 |
| 并发 | 事务内重查，测试顺序竞争 | 未做高并发压力测试和分布式排期 |
| 合成审核 | 标签检查结果可复现 | 不代表实际内容安全或法律判断 |

GitHub Actions 自动运行 Python 3.10、3.12 的同一组测试和场景断言。运行状态以仓库 Actions 页面为准，CI 也只验证离线流程，不调用真实模型。

## 9. 本轮验证结果

本轮执行日期、测试数量、退出码和场景断言摘要以 `examples/verification-summary.json` 为准。文档、目录拆分及代码模块拆分之后，重新执行测试和示例生成；不引用上一目录的历史测试日志。

## 10. 自动化配置来源

CI 使用 GitHub 官方 [actions/checkout](https://github.com/actions/checkout) 和 [actions/setup-python](https://github.com/actions/setup-python) 的 v7，contents: read，不保存 Git 凭据，不调用第三方模型。
