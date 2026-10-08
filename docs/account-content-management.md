# 账号内容工作台

## 启动与数据位置

在技能根目录运行：

```powershell
python -m scripts.manage_content --open
```

服务默认仅监听 `http://127.0.0.1:8765`，数据保存在 `feedback/manager-data/manager.sqlite3`。可以设置端口、数据目录，并导入配置：

```powershell
python -m scripts.manage_content --port 8765 --data-dir "D:\内容管理数据" --config examples/account_config.json --open
```

[示例配置](../examples/account_config.json)的三个绑定均为模拟模式，分别对应微信公众号、今日头条、小红书。模拟不是这些平台的真实账号或接口；可先验收管理和填充链路，再配置实际账号。

工作台提供账号、平台绑定、风格编辑、配置 JSON 导入导出、内容生成/模型稿导入、目录打开、草稿填充、发布关联、状态回收与轮询。浏览器助手安装说明见 [browser-helper.md](browser-helper.md)。不用助手仍可管理内容、导出文件、查询 API/模拟状态。

## 账号 → 平台 → 风格 → 内容版本

1. 创建风格：名称、语言（zh/en）、目标读者、语气、适合平台的 format、风格说明、作者样文和禁用主张。
2. 创建账号：唯一 ID、显示名称、默认输出目录。禁用账号不能新建内容。
3. 创建平台绑定：账号、平台、预期浏览器账号、默认风格、可选输出目录与适配器。
4. 选绑定，填写标题和原文，生成本地预检版本；或导入模型返回的完整 publication JSON。
5. 检查审稿结果与实际文件。`ready_for_human_review` 仍是待人工终审；本地生成始终为 `needs_human_review`。

同一平台可绑定多个账号；每个账号可以绑定多个平台，每个任务也可以选择其他已配置风格。配置保存在 SQLite，重新启动保留。已有内容的绑定不能删除或换成另一个账号/平台身份；需要新建绑定，保证历史归属。

配置契约见 [management.schema.json](../schemas/management.schema.json)。高级编辑用于保留 selectors、status_mapping、接口信息与审稿门槛等结构化字段。风格不存放任务事实：facts 由当前内容输入提供，作者样文只用于风格。

## 输出目录与命令行

优先级：单次任务 → 平台绑定 → 账号 → 工作台数据目录下的 exports。单次内容风格字段优先于风格预设；平台身份由绑定确定，不能用任务覆盖到另一平台。

相对目录以导入配置文件所在目录解析；界面保存的新配置保持原基准，未导入配置时以数据目录解析。中文、空格和绝对路径均支持。目录不允许包含 `..`；系统不可写位置直接报错，不回退到别处。

每版导出目录：

```text
<输出根目录>/<account_id>/<platform>/<content_id>/<version_id>/
  *.md              实际正文
  publication.json  标题、正文、摘要、标签、媒体等完整发布组合
  review.json       本地审稿或导入来源记录
  manifest.json     账号、绑定、风格摘要、输入、版本及内容摘要
```

新版本生成唯一 version_id，不覆写旧版本。同一账号同一平台内使用已有 content_id 可归为同一内容的后续版本。目录打开按钮使用 Windows 文件资源管理器。

旧 CLI 保持兼容；增加账号管理导出：

```powershell
python -m scripts.run_skill examples/input_wechat.json --account-config examples/account_config.json --binding demo-wechat --data-dir feedback/manager-data --json-out managed-output.json
```

已导入过配置时可以省略 `--account-config`，保留 `--binding` 与同一个 `--data-dir`。结构化结果仍包含实际正文和平台稿，并增加 `managed_content` 台账记录。管理模式每版一种语言；双语分别创建版本。

## 一键打开与填充

安装并启用 [browser-helper](browser-helper.md) 后，打开管理页，点击某版本的“打开并填充”。任务打开目标编辑页，核对账号、预检字段、填充并回读；成功后记录 `filled`。不点击保存、提交或发布。

模拟模式打开本地 mock-editor.html，账号、内容 ID 和字段均为模拟对象。实际平台模式需配置编辑 URL、真实页面账号和字段选择器，并在当前登录会话验证。没有有效映射会报错，不靠猜测继续填。

示例结构（选择器值必须换成现场验证的映射）：

```json
{
  "mode": "browser",
  "editor_url": "https://mp.weixin.qq.com/",
  "collector_url": "https://mp.weixin.qq.com/",
  "selectors": {
    "account": "",
    "title": "",
    "body": "",
    "summary": "",
    "tags": "",
    "content_id": "",
    "status": "",
    "metrics": {}
  },
  "status_mapping": {}
}
```

此结构不是可执行的微信公众号映射。编辑器 URL 应是账号实际可用的编辑页；collector_url 可包含 `{content_id}` 占位符，其内容会 URL 编码。

已有非空草稿不覆盖；错账号、登录失效、字段不存在/不唯一、内容不一致、页面加载超时都会留下错误。相同待执行任务复用 task_id，避免连续点击创建重复任务。任务结果未响应时管理页报告失败；服务也会终止过期任务。

当前助手支持普通 input/textarea/contenteditable 的文字填充。富文本 iframe、专用编辑器和媒体上传需相应扩展适配，当前不会冒充已完成。真实小红书图文缺少媒体时返回 needs_media，有媒体但无法上传时返回 media_upload_unsupported。首次交付包含配置与模拟验收，三个平台现场登录、富文本和媒体验收仍须分别完成。

## 发布关联与状态回收

实际发布由用户在平台完成后，在版本中关联真实平台内容 ID、链接及可选的带时区发布时间。关联本身只记录手工信息，不自动确认发布。

点击“立即回收”，或配置 10–86400 秒的轮询（默认 60 秒）。API/mock 轮询由服务执行；停止服务会停止轮询，已启用设置保留。浏览器回收使用辅助扩展，轮询仅在管理页可见、未编辑且无同内容任务执行时发起；隐藏页和输入期间暂停，返回页面后恢复。失败按配置间隔退避，可随时停止后续轮询。

状态与传输结果分开：业务状态为 unknown/draft/scheduled/processing/published/rejected/removed；查询结果为 succeeded/failed。每条快照带 source、观测时间、可选的上游观测时间与指标。失败保留上次成功值并显示失败；旧值显示 stale。缺失指标为 null。

### 模拟模式

```json
{"mode":"mock","mock_status":"processing","mock_metrics":{"reads":12}}
```

通过配置改变 mock_status 演示发布、驳回和移除。模拟值始终标记 mock，不能作为真实状态、传播成绩或阈值校准数据。

### API 模式

```json
{
  "mode":"api",
  "endpoint":"https://your-authorized-service.example/status/{content_id}",
  "token_env":"CONTENT_STATUS_TOKEN",
  "status_mapping":{"online":"published","reviewing":"processing"}
}
```

这里只展示用户授权服务的通用 GET 接口契约，不代表三个平台都有可用开放接口。endpoint 使用 HTTPS，本地测试允许 loopback HTTP；拒绝重定向。凭证从 token_env 指向的本机环境变量读取，使用 Bearer 认证，不保存到配置文件。

返回示例：

```json
{
  "ok":true,
  "account":"实际账号名称",
  "platform_content_id":"平台内容 ID",
  "raw_status":"online",
  "observed_at":"2026-10-04T10:00:00+08:00",
  "metrics":{"reads":123,"shares":4}
}
```

必须核对 account 和 platform_content_id；业务错误、畸形响应、超时、错误身份、非法时间和指标均记录查询失败。原始状态保留，未映射状态为 unknown。计数指标必须是非负安全整数；watch_seconds 可为非负小数。

### 浏览器模式

回收页必须提供账号、内容 ID、状态映射；逐项核对后再读取指标。通过标题猜测内容不予接受。可见指标不可解析时保留 null。轮询只表示定期观测，平台本身的延迟与限流仍存在，界面提供实际查询时间。

状态快照当前保存在管理台账，不自动写入 publication_metrics.jsonl；现有 editorial 命令仍可按真实观察窗口另行录入，避免模拟或未确认记录污染发布反馈。

## 验证命令

```powershell
python -m unittest tests.test_content_manager tests.test_publication_status tests.test_manager_http tests.test_manager_integration tests.test_manager_review tests.test_managed_cli
node --test tests/test_browser_helper.cjs
node --test tests/test_manager_ui.cjs
```

后端 HTTP 测试使用本地真实 HTTP 服务，覆盖账号/内容身份、业务错误和最后成功记录保留；这不等于三个平台 API 验收。浏览器助手测试使用可控 DOM 与扩展 API 测试替身；配置真实账号、现场页面、素材与已发布内容后才能完成平台验收。
