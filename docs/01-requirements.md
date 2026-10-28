# 01 需求说明

## 1. 业务问题与用户

内容运营每天需要处理素材状态、审核风险和发布时间安排。仅生成一段“建议 19 点发布”的文字不足以完成业务：素材可能缺版权、规则可能阻断、时段可能被占用，保存也可能失败。本项目以可核对的工具返回为依据，形成一份可供人工确认的排期草稿。

主用户为内容运营人员；审核人员关注风险与证据；评审者通过可复制命令、测试和 Trace 验证系统行为。

## 2. 本次目标

1. 对单个素材读取元信息，检查必填项和合成规则。
2. 查询请求时段与候选时段的可用性。
3. 允许模型观察结果后选择继续查询、保存或停止。
4. 对柔性时间提出替代草稿，并明确等待人工确认。
5. 对硬性时间冲突保持约束，不自动更改。
6. 明确报告草稿保存成功、重放、失败与任务未完成。
7. 保存输入、实际输出和逐步执行记录以支持复现。

## 3. 范围与排除项

本次只实现单素材、离散固定时段、单机本地 SQLite、CLI、合成规则、单 Agent。支持真实模型 HTTP 决策入口和离线 Mock。业务数据无真实用户或公司内部内容。

没有真实发布能力、素材上传、真实内容语义审核、视频分析、用户登录、审批平台、Web UI、线上部署、多 Agent 或生产级运行时。题目未要求这些能力，当前工作量集中在可验证的核心链路。

## 4. 输入契约

| 字段 | 类型和默认 | 业务意义 | 缺失或异常时的边界 |
| --- | --- | --- | --- |
| material_id | 字符串，必需 | 素材库主键 | 查不到时返回缺失，不生成虚构素材 |
| requested_slot | 字符串，必需 | 带时区的完整发布时间 | 缺失不能保存；不在目录中按不可用处理 |
| hard_time | JSON 布尔，缺省 true | 是否必须保持指定时间 | true 禁止替代；false 只允许保存待确认替代草稿 |

示例：`{"material_id":"M01","requested_slot":"2026-11-01T18:00:00+08:00","hard_time":false}`。

当前未实现完整 JSON Schema 或时间解析；工具依赖字符串精确匹配。调用方应按上述类型提供数据，不能将字符串 `"false"` 作为布尔值。后续输入校验工作列为已知限制。

## 5. 合成资料

`data/catalog.json` 有四部分：

- materials：M01 信息完整无风险；M02 带 unverified_claim 风险标签；M03 缺版权字段。
- rules：阻断标签列表，命中即不保存。
- slots：同一天 18、19、20 点三个离散时段，UTC+08:00。
- occupied：默认 18 点已占用。

规则与素材均是本项目的合成数据，不代表任何公司的真实审核标准。素材“无风险”仅指通过当前标签检查，不是法律或内容安全结论。

## 6. 输出契约

| 字段 | 说明 |
| --- | --- |
| status | completed / needs_confirmation / blocked / failed / incomplete |
| reason | 简短决策依据或异常类型，无模型内部思维 |
| draft | 最近一次保存返回，可能为 null；失败或步数上限路径可能没有此字段 |
| published | 恒 false，表示本项目没有执行发布 |
| mode | mock 或 live，由 CLI 或示例生成器添加 |
| trace | 工具调用顺序、参数、工具结果和简短依据 |

草稿成功返回含 draft_id、material_id、slot、requested_slot、confirmation、duplicate。confirmation 为 not_required 表示草稿保持原请求时段；pending 表示替代时间需要确认。二者均只涉及草稿。

风险原因来自 check_rules 的 risks；缺失项来自 missing；建议时段来自 query_slots 或成功草稿。暂未将这些字段再聚合为独立的审核报告对象，消费者需读取 Trace。此项明确列为交付展示层的限制。

## 7. 成功标准与验收映射

| ID | 场景 | 期望行为 | 证据入口 |
| --- | --- | --- | --- |
| A01 | 正常排期 | 审核通过，原时段可用，保存一份草稿，completed | normal.trace.json；test_normal_and_duplicate |
| A02 | 素材信息缺失 | 缺素材或版权时阻断，不写入数据库 | missing / missing_metadata Trace；test_missing_and_risk |
| A03 | 规则风险 | 返回命中风险，不保存 | risk.trace.json；test_missing_and_risk |
| A04 | 柔性时段冲突 | 观察冲突后选择可用替代时间，保存 pending | conflict.trace.json；test_flexible_conflict |
| A05 | 硬性时段冲突 | 不擅自改变，needs_confirmation，无草稿 | hard_conflict.trace.json；test_hard_conflict |
| A06 | 重复提交 | 相同草稿载荷重放，返回相同 draft_id，数量不变 | duplicate.trace.json；test_normal_and_duplicate |
| A07 | 保存失败 | failed，ok=false，不伪称成功 | save_failure.trace.json；test_save_failure |
| A08 | 无候选时间 | blocked，说明缺口 | no_slots.trace.json |
| A09 | 结果扰动 | 改占用或规则后路径改变 | changed_occupied / changed_rule Trace |
| A10 | 有界运行 | 到上限返回 incomplete | step_limit.trace.json；test_limit_and_false_success |
| A11 | 模型越过工具约束 | 无前置观察不能保存；无证据成功被纠正 | test_prerequisites；test_limit_and_false_success |
| A12 | 真实模型动态决策 | 至少两条真实运行记录体现不同观察下不同动作 | 待真实模型运行，当前未完成 |

表中 Trace 均位于 examples，当前已生成的是离线记录。A12 不得由 A01–A11 的 Mock 测试代替。

## 8. 用户确认的边界

硬性时间冲突时，当前流程返回待确认并停止。运营人员可以指定新的 requested_slot 再运行；项目没有独立的审批记录、用户身份或审批凭证，因此不声称实现了完整审批闭环。柔性时间替代只生成 pending 草稿，不会自动变成确认状态或触发发布。

## 9. 完成判定

工程可运行与真实模型验收分开记录：离线测试通过只代表当前已测约束成立；真实模型路径、资料扰动、本人核实贡献以及最终 GitHub URL / SHA 仍是正式提交前的工作。
