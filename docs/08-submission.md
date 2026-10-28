# 第 1 题提交说明

## 交卷字段

题号：1（素材审核与发布排期 Agent）。

GitHub URL：https://github.com/Lucky-Ray/material-scheduling-agent

仓库可见性：公开，评审不需要额外读取权限。

最终 commit SHA：以交卷时 `git rev-parse HEAD` 输出为准，并与 `git ls-remote origin refs/heads/main` 比较；不把会随更新变化的 SHA 写死在仓库内。

## 可复用的项目说明

本项目实现单素材审核与排期草稿链路，包含素材读取、规则检查、时段查询、SQLite 草稿保存、硬性时间保护、替代时段待确认和请求级防重复。模型接入为逐步 JSON 动作协议；每步接收已有工具观察后再决定下一步，执行器保留工具参数、结果及简短决策依据。工具独立校验保存约束，无真实发布接口。

工程采用 Python 标准库，可通过 CLI 运行。已提交需求、方案、评估、AI 使用披露和复盘等材料，现有 19 项单元测试及 12 组离线场景断言通过。GitHub Actions 自动执行离线测试；示例中明确 mode=mock。

当前限制：本轮未执行真实模型验证，因此现有证据仅证明工具与执行流程，不能证明真实模型动态决策效果；无生产级审核、人工审批平台、分布式排期。AI 辅助范围和本人尚待核实的贡献在 docs/04-ai-usage.md 中如实披露。

## 评审复现

```powershell
python -m unittest discover -s tests -v
python examples/generate.py
python src/agent.py --input examples/conflict.input.json --mode mock --db :memory:
```

真实模型复现方法见 README 第 4 节。正式交卷前需由候选人核对上述限制与题目要求；当前未登录考试平台，未代点交卷按钮。
