# 本机内容浏览器助手

`browser-helper/` 是无外部依赖的 Chrome / Edge Manifest V3 扩展。使用浏览器已经登录的会话，打开目标页，核对账号后填充字段或读取状态。扩展没有保存、提交、发布按钮操作，不存储 Cookie、密码或管理会话 Token。

## 安装与操作

1. Chrome 打开 `chrome://extensions`，Edge 打开 `edge://extensions`，启用开发者模式。
2. 点击“加载已解压的扩展”，选择本技能根目录下的 `browser-helper` 文件夹。
3. 启动本机管理服务，在同一个浏览器打开管理页；安装或更新扩展后刷新管理页。
4. 真实平台先在该浏览器登录所需账号。绑定中配置实际编辑/状态页面地址和现场确认的选择器。点击管理页的填充或回收按钮。
5. 目标页会在新标签页打开。填充成功只证明当前页面字段回读匹配，不证明平台已保存草稿、发布或后台持久化。

安装目录必须包含 manifest.json、runner.js、background.js、bridge.js。扩展权限限定本机 HTTP 和三个创作者后台 HTTPS 域名；网站重定向到其他域名会返回 url_rejected。页面载入最多等待 20 秒。只接受顶层本机管理页发来的请求，baseUrl 必须与管理页同源，模拟任务也必须同源。

## 请求与结果

管理页向自己的 window 发送：

```javascript
window.postMessage({
  type: 'MIDNIGHT_REQUEST', requestId: '唯一请求编号',
  baseUrl: location.origin, token: '当前管理会话凭证',
  task: {
    id: 'task-1', binding_id: 'binding-1', kind: 'fill', platform: 'mock',
    url: location.origin + '/mock-editor', expected_account: '账号显示标识',
    content_id: '内容标识', overwrite: false,
    publication: {selected_title: '标题', body: '正文', summary: '', tags: [], media: []},
    selectors: {account: '#account', title: '#title', body: '#body'}
  }
}, location.origin);
```

响应为 `{type:'MIDNIGHT_RESPONSE',requestId,result}`。页面必须校验 event.source、event.origin、requestId 并用自己的管理凭证将结果提交给本机服务；扩展不直接写台账。Token 只做请求格式检查，服务端仍须验证会话。来源 browser/mock 只用于区分执行路径，不是不可伪造的远程证明。正在执行的同一 origin/task.id 共用操作；已完成任务的恢复和去重由管理服务负责。

填充成功返回 `{status:'filled',source:'browser'|'mock',changed_fields:[...]}`。先检查所有待写字段的唯一性、可编辑性、已有值和重叠，再使用原生 value setter 或 contenteditable textContent 替换，派发 input/change 并回读。正文按纯文本填充，不声称富文本排版一致。默认非空草稿返回 nonempty_draft；只有明确 overwrite:true 才替换，正常管理流程不会设置它。

已配置摘要或标签选择器时，即使本次摘要/标签为空，也会检查这些字段是否含有已有内容；已有内容阻止全部写入。空白目标会写入并回读空值，显式 overwrite:true 会清空旧摘要/标签，避免正文与旧可选字段混合。

回收任务 kind 为 collect，selectors 必须包括 account、content_id、status，可配置 metrics 下的 impressions、clicks、reads、completions、saves、shares、comments、conversions、watch_seconds。账号和内容 ID 都必须精确匹配；不凭标题猜测。成功返回 `{status:'collected',platform_content_id,raw_status,metrics,source}`，业务状态映射由管理服务执行。计数指标只接受非负安全整数的十进制原始文本，watch_seconds 允许有限的非负小数；“1.2 万”、负数、空白、无效值均为 null，零保持为 0，缺省指标由管理层保持不可用状态。task.id 与 binding_id 必须符合管理层的 1–80 位字母/数字/下划线/连字符标识规则；扩展检查格式，绑定归属由服务端检查。

错误区分 needs_login、account_mismatch、content_id_mismatch、capability_unverified、selector_missing、selector_not_unique、selector_invalid、selector_overlap、unsupported_field、field_not_editable、nonempty_draft、readback_mismatch、write_failed、url_rejected、page_timeout、tab_closed 等。write_failed/readback_mismatch 可能已有字段写入，会返回 changed_fields；停止自动重试，检查当前草稿。

## 真实平台验证边界

三个真实平台没有内置猜测选择器，初始能力为 unverified。需在当前已登录会话确认账号、编辑字段、内容 ID、状态和指标选择器且结果唯一，完成真实页面测试后才能另行登记 verified。当前选择器执行器不支持跨框架 iframe、复杂富文本编辑器或媒体上传；需要独立适配及现场测试。小红书未提供媒体返回 needs_media，提供媒体仍返回 media_upload_unsupported，不能冒充图文填充成功。其他平台携带媒体也返回 media_upload_unsupported。

Node 测试使用轻量 DOM fixture 执行同一个导出的注入函数，验证账号/ID、预检、替换、回读、指标、URL 和消息边界；这不是浏览器安装验收或三个平台真实账号 E2E。执行 `node --test tests/test_browser_helper.cjs`。

MV3 注入和异步消息使用 Chrome 官方文档约定：[函数与参数注入](https://developer.chrome.com/docs/extensions/develop/migrate/improve-security)、[异步消息](https://developer.chrome.com/docs/extensions/develop/concepts/messaging)。
