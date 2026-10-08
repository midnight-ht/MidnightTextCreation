# n8n Workflows

推荐优先使用：

```text
n8n_model_nodes_workflow.json
```

它使用：

```text
Basic LLM Chain + OpenAI Chat Model
```

导入后配置 `OpenAI Chat Model` 节点凭证，它连接所有模型链路。

链路包含选题张力、结构、初稿、规则扫描、模型 Judge、有限轮次重写、平台适配和模型 Viral Judge。每次只接收一个平台、一种语言（zh/en）。

升级链路在选题后增加三候选的成对比较，在平台适配后增加事实、风格、表达、传播四维审稿。作者样文、带来源的事实和禁用主张会进入写作与重写上下文。没有样文时，风格审稿返回未知并转人工复核。

可通过 `review_thresholds` 配置四项门槛，默认值见 `rules/editorial_rules.json`，尚需人工样例校准。新增节点同步命令：`node scripts/upgrade_workflow.cjs`。

平台适配后明确选择 selected_title，对标题、封面文字、正文复核。有明确修复意见时进入最终稿重写，并再次规则扫描和四维审稿，预算与初稿重写共享。解析失败从对应检查出口返回 stage_error；模型调用错误交由解析节点转换为复核或错误响应。

风格模板以请求字段 style_guidance 传入文本。n8n 不读取客户端本地路径。

Judge 解析失败立即转人工复核；重写后读取当前轮次状态并重新扫描。平台适配或传播审稿解析失败、传播分低于 40 或风险高时也转人工复核。

HTTP Request 文件目前只是占位说明，尚未实现，不能导入执行：

```text
n8n_http_request_workflow.json
```

在项目根目录运行 `node tests/test_workflow.cjs` 可验证代码节点与图结构。真实 n8n 运行仍需要服务和模型凭证。
# 平台排版扩展

`rules/platform_layouts.json` 是平台内容形态与排版方法的单一配置来源。运行 `node scripts/upgrade_workflow.cjs` 会同步输入平台/格式枚举、旧平台规则、输出 layout_plan 合约和模型节点。

工作流一次请求一个平台及一种形态，例如 `{"platform":"wechat_channels","format":"script"}`。模型收到 `platform_profile`：内容顺序、段落、强调、配图与发布步骤；正文用空行划分卡片/帖子/口播单元。最终审稿检查所选形态，修订后重建 layout_plan，避免旧分块引用旧正文。

`layout_plan.blocks` 是有序文本工作稿，不是已渲染卡片、视频、原生富文本或已发布内容。当前账户的长度、裁切、字幕安全区、链接和权限需要在平台预览中另行核验。完整规则见 `rules/platform-formatting-guide.md`。
# 端到端链路边界

完整生产操作规范见 `references/content-production-pipeline.md`，任务记录见 `templates/content-production-task.md`。本 n8n JSON 实现的是模型文案流程，输出仍待人审；没有因文档整理而新增图片/音视频渲染、商业审批或平台发布节点。人工/外部工具完成的制作、验收、批准和发布分别记录，不能用流程模拟代替实际证据。
