# midnight-advertorial

用于中文、英文内容的反模板化审稿、定向改写与平台适配的 Codex Skill。适用于文章、软文、图文文案、视频脚本及 AI 初稿发布前质检。

核心原则：先确认事实与选题张力，再处理结构、表达和排版。规则扫描用于发现套话和结构信号，不能鉴定文本是否由 AI 撰写；传播评分用于编辑参考，不预测实际流量。

## 从哪里开始

| 需求 | 入口 |
| --- | --- |
| 在 Codex 中写作、改稿或审稿 | [SKILL.md](SKILL.md) |
| 本地扫描初稿、导出 Markdown | 本文的快速使用与输入说明 |
| 接入模型审稿和限次改写 | [工作流说明](workflows/README.md) |
| 制作文章、商业软文、图文或视频发布包 | [完整生产链路](references/content-production-pipeline.md)与[任务模板](templates/content-production-task.md) |
| 选择国内外平台与排版形态 | [平台排版手册](rules/platform-formatting-guide.md) |
| 查看制作工具路线与调研依据 | [内容生成调研报告](reports/content-generation-research-2026-10-04.md) |
| 管理账号、平台风格、输出目录与发布状态 | [账号内容工作台](docs/account-content-management.md) |

## 账号内容工作台

新增本地管理页，按“账号 → 平台绑定 → 风格 → 内容版本”管理内容，支持独立输出目录、模型稿导入、草稿填充和发布后状态回收：

```powershell
python -m scripts.manage_content --open
```

默认地址为 `http://127.0.0.1:8765`。首次使用可导入 [账号配置示例](examples/account_config.json)，或在管理页创建账号、风格与平台绑定。示例中微信公众号、今日头条、小红书均为模拟模式。

输出目录支持账号默认、平台覆盖、任务覆盖；每个内容版本单独导出正文、发布组合、审稿与台账。原命令行新增 `--account-config`、`--binding`、`--data-dir`，具体用法见[工作台说明](docs/account-content-management.md)。

“打开并填充”需要安装 [Chrome/Edge 浏览器助手](docs/browser-helper.md)。助手核对账号、填充字段并回读，停在草稿；真实平台需现场配置和验证字段映射。当前普通文字字段可填，专用富文本编辑器和媒体上传可能不支持，错误会明确返回。

状态回收支持 API、浏览器与模拟，显示来源、观测时间、查询失败及上次成功结果。API/模拟轮询由本地服务执行，浏览器轮询在管理页可见且未编辑时执行。示例与模拟检查不能代替三个平台真实账号验收。

## 能力与执行模式

| 项目 | 本地模式 `local_deterministic` | 模型模式 `strict_model_workflow` |
| --- | --- | --- |
| 入口 | `scripts/run_skill.py` | `workflows/n8n_model_nodes_workflow.json` |
| 文案处理 | 输入归一化、规则扫描、轻量清理 | 选题张力、三候选成对比较、结构规划、初稿 |
| 审稿与改写 | 确定性检查与启发式建议 | 规则扫描、模型 Judge、限次改写、最终四维审稿与修订、Viral Judge |
| 平台适配 | 保留原文的格式化与分块计划 | 按目标平台进行语义适配并复审 |
| 事实与作者风格 | 语义审稿标记为未评估 | 根据提供的证据和样文评审；缺少依据时返回未知 |
| 多平台与语言 | 支持 `platform_configs`；双语拆为两个输出，不执行翻译 | 每次请求一个平台、一种语言（`zh` 或 `en`） |
| 结果状态 | 始终为 `needs_human_review` | 待人工终审、待复核或失败 |

本地模式不调用大模型，不生成新文章，也不进行语气改写或候选比较。作者样文只用于风格参考，不能转化为新文章中的虚构亲身经历。提供来源信息也不代表事实已经独立核验。

完整生产链路是辅助操作规范。当前脚本和模型工作流未自动实现图片渲染、配音、视频合成、商业审批或平台发布。

## 快速使用

以下命令在本目录运行。本地脚本使用 Python；工作流检查与同步脚本使用 Node.js。

### 在 Codex 中使用

技能已被 Codex 识别时，可直接提出任务：

```text
使用 $midnight-advertorial 审核这篇公众号初稿。
目标读者是内容编辑，保留核心观点，先指出事实和结构问题，
再定向改写，输出 Markdown 与人工终审清单。
```

写作任务应提供主题、目标读者、内容目标、平台和语言，并尽量附上原稿、事实来源、作者样文与禁用主张。完整交付任务使用[创作与交付模板](templates/content-production-task.md)记录范围和阶段证据。

### 仅扫描规则

```bash
python -m scripts.rule_scan examples/input_wechat.json
python -m scripts.rule_scan --text "This is an English draft." --language en
```

JSON 文件扫描默认按中文规则执行；检查英文时显式指定 `--language en`。

### 运行本地流程

```bash
python -m scripts.run_skill examples/input_wechat.json --json-out output.json
```

脚本输出结构化 JSON，并导出 Markdown。`output_dir` 默认是技能根目录，可在输入中指定其他目录；风格模板未找到时会创建 `风格模板.md`。多平台示例：

```bash
python -m scripts.run_skill examples/input_platform_layouts.json --json-out platform-output.json
```

此示例演示平台结构，英语目标不会自动获得英语译稿。需要英文输出时，应提供英文原文或使用模型流程。

### 模型工作流

使用 [n8n 模型节点工作流](workflows/n8n_model_nodes_workflow.json)，导入与凭证说明见[工作流文档](workflows/README.md)。模型链路为：

```text
选题张力 → 三候选成对比较 → 结构 → 初稿
→ 规则扫描与 Judge → 限次改写
→ 平台适配 → 选择实际标题 → 四维审稿与修订
→ Viral Judge → 待人工终审
```

初稿改写与最终稿修订共享 `max_rounds`。最终复审覆盖实际标题、封面文字、摘要、正文、开头和标签；修订时重新生成完整发布组合。解析失败、缺证据、未解决的问题或高风险均不能作为通过结果。

`n8n_http_request_workflow.json` 目前只是占位说明，不能导入执行。现有工作流测试使用模拟模型响应，真实 n8n 节点兼容性与模型调用仍需在配置服务和凭证后验证。

## 输入说明

完整契约见 [input.schema.json](schemas/input.schema.json)，审稿素材示例见 [input_editorial.json](examples/input_editorial.json)。

```json
{
  "title": "发布前怎样检查 AI 初稿",
  "platform": "wechat",
  "language": "zh",
  "target_reader": "内容编辑",
  "content_goal": "检查事实、结构和标题承诺，交付待终审稿",
  "raw_material": "这里放原稿或真实素材",
  "core_opinion": "先检查判断和事实，再修词句",
  "tone": "直接、清晰，不要营销腔",
  "author_samples": [],
  "facts": [],
  "forbidden_claims": ["保证十万加"],
  "style_template": "practical-essay",
  "output_dir": "output",
  "max_rounds": 2,
  "pass_score": 25
}
```

| 字段 | 用途 |
| --- | --- |
| `raw_material` | 原文或素材；本地模式不补写缺失素材 |
| `author_samples` | 真实作者样文，只供语气、节奏和表达参考 |
| `facts` | 事实数组，每项包含唯一 `id`、`claim`、`source` |
| `forbidden_claims` | 不允许使用的主张 |
| `style_template` | 本地风格模板名称或文件路径；模板内容写入 `style_guidance` |
| `style_guidance` | 传给模型工作流的风格文本；n8n 不读取调用方本地模板路径 |
| `platform_configs` | 本地多平台配置，每个平台可设置 `language`、`tone`、`format` |
| `max_rounds` | 改写轮次预算，整数 0–10，默认 2 |
| `pass_score` | AI 味评分门槛，整数 0–100，默认 25；分数越低表示命中信号越少 |
| `review_thresholds` | 风格、表达、传播和 Viral Judge 门槛，配置键见技能契约 |

无效平台、语言、格式、非整数轮次和数字字符串会报错。四维门槛默认值见 [editorial_rules.json](rules/editorial_rules.json)，目前尚未经过真实人工样例校准。

## 平台与排版

[平台配置](rules/platform_layouts.json)覆盖 34 个平台／内容入口：15 个国内入口、16 个国外入口、3 个通用入口。完整平台键和原生发布检查见[排版手册](rules/platform-formatting-guide.md)。

可用形态包括 `long_form`、`short_post`、`carousel`、`thread`、`script`、`spoken`、`text`；每个平台仅接受其配置允许的形态。本地通过 `platform_configs.<平台>.format` 选择，模型工作流通过单次请求的 `platform` 和 `format` 选择。

`platform_output.layout_plan` 包含原文分块和发布步骤。卡片文本、线程分块和视频脚本仍是文字工作稿；实际图片、成片和原生编辑器预览需另行制作与验收。编辑建议不等于平台硬性限制，发布前应核对目标账号当前规则。

## 输出与结果状态

结构化输出契约见 [output.schema.json](schemas/output.schema.json)。主要结果包括：

- `rule_scan`、`ai_slop_score`：规则命中、结构信号与评分。
- `judge_result`、`editorial_review`、`viral_judge_result`：问题、修订建议及审稿结果；本地语义未知项明确标记。
- `candidate_comparison`、`structure_json`：候选比较或未评估说明，以及结构建议。
- `final_text`、`platform_output`：实际导出正文、平台发布组合、视觉提示和排版计划。
- `platform_output.files`、`outputs`：导出文件与各平台／语言结果。
- `human_review_checklist`：人工终审清单。

| 状态 | 含义 |
| --- | --- |
| `ready_for_human_review` | 模型流程满足检查条件，等待人工终审 |
| `needs_human_review` | 存在未知、未评估、未解决问题或风险，需人工复核；本地结果统一使用此状态 |
| `failed` | 流程失败，按错误信息处理 |

`ok: true` 表示流程返回结果，不能据此认定内容已经获批或发布。

## 完整生产与交付

```text
需求 → 素材／证据／权利 → 选题 → 创作 → 文案审稿 → 平台定版
→ 文章／图文／视频制作（商业内容叠加声明与披露审核）
→ 实际成品验收 → 发布包交付 → 经授权发布 → 复盘归档
```

生产形态与商业属性分别记录。软文可以是文章、图文或视频，需要在对应制作流程上叠加商业事实、声明与披露检查。

使用[完整链路规范](references/content-production-pipeline.md)和[任务模板](templates/content-production-task.md)，分别保留文案版本、实际媒体、验收、人工批准、发布授权及回执。仅交付任务止于发布包，发布阶段标记为 `not_requested`。文案交付或媒体生成任务不自动授权公开发布。

## 校准与发布反馈

人工校准标签使用 JSONL，每行包含 `id`、模型／提示词版本、人工审稿人、`split`（`calibration` 或 `holdout`）以及 human/model 两组四维标签。

```bash
python -m scripts.calibrate_reviews examples/review_labels.jsonl
```

命令报告独立测试集的一致率、误放行、误拒绝、未知分歧与版本分组，不自动修改阈值。[示例标签](examples/review_labels.jsonl)是虚构演示数据，不能作为真实校准依据。

发布反馈示例：

```bash
python -m scripts.editorial examples/publication_feedback.json --log feedback/demo-metrics.jsonl
```

省略 `--log` 时默认追加到 `feedback/publication_metrics.jsonl`。示例指标同样为虚构数据；真实记录应保留内容／候选 ID、平台、观察时间窗和可用指标。缺失指标保持为空，观察性记录与随机实验分开，不自动判定胜者或推断因果。轻量编辑反馈可记录在 `feedback/content_feedback_log.jsonl`。

## 目录

```text
SKILL.md     技能入口、输入契约与执行规则
agents/      Codex 技能展示与调用配置
prompts/     选题、写作、审稿、改写与平台适配提示词
rules/       语言规则、评分配置、平台排版库与手册
schemas/     输入、审稿与输出 JSON Schema
scripts/     本地扫描、导出、校准、反馈与工作流同步工具
workflows/   n8n 模型工作流及接入说明
manager/     账号内容工作台与模拟编辑页
browser-helper/ Chrome/Edge 草稿填充与状态读取扩展
docs/        工作台使用、设计与实施说明
styles/      可复用作者风格模板
examples/    输入、输出与演示标签／指标
references/  完整生产链路规范
templates/  创作与交付任务模板
reports/     工具路线与调研依据
feedback/    编辑反馈与指标记录
tests/      本地逻辑、平台排版与模拟工作流检查
```

## 验证与维护

```bash
python -m pytest tests
```

未安装 pytest 时，可运行以下本地检查：

```bash
python -m tests.test_runner
python -m unittest tests.test_editorial tests.test_platform_layout
node tests/test_workflow.cjs
```

检查覆盖本地输入与导出、规则处理、平台分块、审稿契约及模拟工作流状态。模拟通过不能替代真实模型运行、媒体成品验收或平台发布核验。

调整提示词、审稿规则或平台配置后，同步生成工作流：

```bash
node scripts/upgrade_workflow.cjs
```

同步后检查变更、运行相关检查，并重新导入更新后的 n8n 文件。同步脚本不会调用模型或发布内容。

