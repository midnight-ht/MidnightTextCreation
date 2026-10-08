# 账号内容管理验证记录

日期：2026-10-04（Asia/Shanghai）。范围：技能本地管理版本 1.1.0。

## 实际交付

- SQLite 账号/平台绑定/风格配置与内容版本台账，配置导入导出。
- 输出目录覆盖和账号隔离版本文件，兼容原 runner，并支持 --account-config/--binding/--data-dir。
- 本地内容工作台、Chrome/Edge MV3 辅助扩展、可执行模拟编辑页。
- 草稿填充任务、账号/内容身份校验、已有草稿保护、完整映射字段回读。
- API/browser/mock 状态回收，查询失败与业务状态分开，保留最后成功，显式来源/时区/新鲜度。
- API/mock 服务轮询及可见管理页浏览器轮询、停止与退避。
- SKILL、README、配置 Schema、示例和使用说明同步。

## 当前验证结果

| 检查 | 结果 | 证明范围 |
| --- | --- | --- |
| python -m tests.test_runner | 10 项 PASS | 原有本地 runner 检查 |
| 标准库 unittest：editorial/layout/manager/status/http/integration/review/managed_cli | 49/49 通过 | 现有与新增 Python 行为 |
| node tests/test_workflow.cjs | PASS | 模拟模型节点、图结构及脚本合法性 |
| node --test tests/test_browser_helper.cjs tests/test_manager_ui.cjs | 48/48 通过 | 38 项浏览器助手、10 项界面行为；使用测试 DOM/扩展 API 替身 |
| JS 语法检查 | 通过 | 扩展后台、管理页和模拟编辑页脚本 |
| 实际本地管理页 | 通过 | 生成版本、真实文件导出、关联模拟内容、回收 mock 状态、重启后持久化 |

pytest 未安装，未安装新依赖；按项目现有替代入口完成验证。Python/Node 检查退出码均为 0。

新增检查曾在实现前失败，并在修复后通过。复核问题包括连接释放、并发任务幂等、类型错误返回、回收失败记录、轮询间隔、上游时区/旧时间、异常指标、草稿可选字段保护及自动刷新保护。

实际管理页面截图：[工作台预览](../docs/account-manager-preview.jpg)。运行地址：[本地工作台](http://127.0.0.1:8765)。示例绑定均为模拟；模拟发布 ID 为 mock-post-1，不是实际平台内容。

## 明确尚未验收

- Chrome/Edge 扩展的用户浏览器安装及真实会话运行。
- 微信公众号、今日头条、小红书当前编辑器的字段映射、账号核验及现场填充。
- 专用富文本编辑器、iframe 和媒体上传；当前助手遇到不支持能力会明确失败。
- 三个平台的正式状态接口权限、真实已发布内容查询、真实传播指标。
- 人工审批、实际平台发布和业务效果。

通用接口测试使用本地真实 HTTP 服务，不能据此宣称真实平台接口已经开通。截图中的 processing 是 mock 结果。实际平台接入需要用户已登录浏览器、现场验证的映射和真实发布内容；当前没有这些证据。
