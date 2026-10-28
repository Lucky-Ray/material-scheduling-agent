# 素材审核与发布排期 Agent

小影校招 AI Agent 项目题，第 1 题。独立项目，所有运行材料位于当前目录，与面试资料目录和既有项目无代码依赖。

本项目帮助运营人员审核一项素材，并在可用时段保存排期草稿。模型观察工具返回后再选择下一步；保存工具独立检查规则、硬性时间和冲突。程序没有发布接口。

**当前交付状态：离线工具和执行流程已验证；真实模型接入已实现，真实模型决策效果尚未验证。当前不能作为完成全部验收的最终提交。**

## 1. 评审阅读顺序

| 材料 | 内容 |
| --- | --- |
| [需求说明](docs/01-requirements.md) | 用户、范围、数据契约、逐条成功标准 |
| [方案说明](docs/02-solution.md) | 模型闭环、模块职责、工具协议、状态与权限、设计取舍 |
| [评估报告](docs/03-evaluation.md) | 测试预期与实际结果、验收映射、失败和限制 |
| [AI 使用说明](docs/04-ai-usage.md) | AI 辅助范围、已运行验证、个人贡献待核实项 |
| [复盘](docs/05-retrospective.md) | 难点、改进、剩余工作与个人复盘边界 |
| [提交检查表](docs/06-submission-checklist.md) | 原题交付条目、当前状态、提交前操作 |
| [运行记录索引](examples/INDEX.md) | 合成输入、实际输出、Trace、场景解释 |

## 2. 环境与安装

- Python 3.10 或更高版本；当前验证环境 Python 3.12.7、Windows PowerShell。
- 只使用 Python 标准库，无 pip 安装步骤；`requirements.txt` 说明无第三方依赖。
- 离线模式不需要联网、模型账号或环境变量。
- 在线模式要求支持 Chat Completions 形式的 HTTP 服务、模型名称和 API Key。

```powershell
Set-Location 'E:\Desktop\秋招\小影校招-Agent'
python --version
python -m unittest discover -s tests -v
python examples/generate.py
python scripts/verify.py
```

`examples/generate.py` 在每个场景中使用独立内存数据库，不污染演示或业务数据库；重复提交场景在同一连接执行两次。生成结果会覆盖同名离线示例文件。

## 3. 离线运行

```powershell
python src/agent.py --input examples/normal.input.json --mode mock --db demo-normal.sqlite3
python src/agent.py --input examples/conflict.input.json --mode mock --db demo-conflict.sqlite3
python src/agent.py --input examples/save_failure.input.json --mode mock --db demo-failure.sqlite3 --fail-save
```

数据库默认相对当前工作目录保存。再次使用同一个数据库会保留草稿占用；需要全新演示时换一个数据库文件名，也可以使用 `--db :memory:`。离线结果只验证流程，MockModel 的固定分支不证明真实模型决策能力。

## 4. 真实模型配置与运行

```powershell
$env:MODEL_BASE_URL='https://your-provider.example/v1'
$env:MODEL_NAME='your-model'
$env:MODEL_API_KEY='your-key'
python src/agent.py --input examples/normal.input.json --mode live --db live-normal.sqlite3 --output examples/live-normal.trace.json
python src/agent.py --input examples/conflict.input.json --mode live --db live-conflict.sqlite3 --output examples/live-conflict.trace.json
```

使用不同数据库隔离两条验证路径。真实请求费用由所选服务产生。`.env.example` 仅为变量模板，程序不自动加载 `.env`。不要把密钥写入仓库或示例结果。

客户端把 MODEL_BASE_URL 与 `/chat/completions` 拼接；每次调用发送 system 提示词、用户业务请求及历史工具记录。服务返回 `choices[0].message.content`，内容必须为 JSON 对象，不支持 Markdown 代码块、流式输出或原生 function calling。HTTP 单次超时 45 秒；暂不自动重试。

至少保留正常路径和冲突路径的真实模型记录，并确认工具结果改变后，下一步确实改变。live 模式执行失败时应如实保存失败，不得改写成成功。详细人工复核步骤见评估报告。

## 5. 输入与输出

```json
{
  "material_id": "M01",
  "requested_slot": "2026-11-01T18:00:00+08:00",
  "hard_time": false
}
```

可选 `request_id` 标识同一业务请求；缺省按素材 ID 与原请求时间防重复，即使模型换候选时段也恢复原草稿。时间必须与合成时段表中的字符串完全一致。`hard_time` 缺省为 true；false 允许提出替代草稿，仍标记为待确认。CLI 输入为单项请求，多素材可逐次调用。

输出包含 `status`、`reason`、`draft`、`material_result`、`published: false`、`mode` 和 `trace`。Trace 的每一项包含步骤、工具、参数、简短依据及完整工具返回。输出本身同时包含实际结果和运行记录，不另造摘要替代事实。

| status | 含义 |
| --- | --- |
| completed | 原请求时段草稿保存成功；不代表已发布 |
| needs_confirmation | 硬时间冲突待确认，或替代时段草稿待确认 |
| blocked | 缺资料、规则风险或无可用时段 |
| failed | 保存、模型、网络或协议失败，或模型无证据声称成功 |
| incomplete | 达到执行步数上限，任务未完成 |

## 6. 命令参数

| 参数 | 默认值 | 用途 |
| --- | --- | --- |
| --input | 必填 | UTF-8 / UTF-8 BOM JSON 输入 |
| --catalog | data/catalog.json | 可指定场景 catalog 快照 |
| --mode | mock | mock 离线；live 远端模型 |
| --db | drafts.sqlite3 | SQLite 草稿存储路径，支持 :memory: |
| --output | 无 | 将完整 JSON 结果写入指定文件；父目录须已存在 |
| --fail-save | false | 新草稿保存故障注入；已有草稿重放仍可返回 |
| --max-steps | 10 | 模型决策循环上限，包含结束动作 |

## 7. 目录和职责

```text
src/
  agent.py      稳定入口及公共导出
  cli.py        命令参数、输入数据与输出
  models.py     真实模型适配器、提示词、离线模拟器
  tools.py      素材、规则、时段、SQLite 保存
  runner.py     有界执行循环、Trace 与结果核验
tests/         可执行测试
data/          合成素材、风险规则、时段及已有占用
examples/      输入、实际离线输出、测试日志、生成器、索引
docs/          需求、方案、评估、AI 披露、复盘、提交检查表
scripts/       一键刷新测试日志、场景和验证摘要
```

## 8. 故障排查与已知边界

- 正常请求突然冲突：先检查是否重复使用已有草稿的数据库。
- 缺少模型变量：在线模型初始化失败；按 `.env.example` 设置全部三个变量。
- 模型返回非 JSON、HTTP 错误或超时：执行结果为 failed，reason 只记录异常类型，避免泄漏服务响应中的敏感内容。
- 文件读取、数据库、模型配置与输出写入失败统一返回结构化 JSON；failed / incomplete 的 CLI 退出码为 1，其余业务结束状态为 0。
- 所有状态都应结合工具证据理解。即使执行异常或到上限，`draft` 和 `material_result.save_status` 仍保留已成功写入的证据。
- 请求级幂等会保持原草稿；修改业务意图需使用新的 request_id。规则更新后，历史草稿重试会重新审核；当前不会自动撤销旧记录。

GitHub 仓库：https://github.com/Lucky-Ray/material-scheduling-agent （公开）。当前上传操作不等于考试交卷；本人仍需完成真实模型验证、理解并修改代码、填写真实贡献。最终 commit SHA 使用 `git rev-parse HEAD` 获取。

## 9. 自动验证和提交入口

GitHub Actions 在 push / pull_request 后验证 Python 3.10 和 3.12 的单元测试及 12 组场景断言，详情见 [Actions](https://github.com/Lucky-Ray/material-scheduling-agent/actions)。运行时不调用远端模型，也不需要密钥。

评审用说明见 [提交说明](docs/08-submission.md)。当前真实模型验证未执行，不把离线通过解释为全题验收通过。
