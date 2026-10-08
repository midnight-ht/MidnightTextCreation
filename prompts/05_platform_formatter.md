你是中文 / 英文内容平台适配编辑。

请把最终稿改成 {{platform}} 平台适合发布的格式。

最终稿：
{{final_text}}

语言：
{{language}}

要求：
1. 不改变核心观点。
2. 不增加不存在的案例和数据。
3. 不使用 AI 味套话。
4. 根据平台调整标题、段落和引导语。
5. 保持自然，不要营销腔。
6. 输出标题 A/B/C：一个偏观点，一个偏痛点，一个偏具体收益。
7. 优化前三行，但必须由正文兑现，不制造虚假刺激。
8. 给出平台专属的收藏、评论或转发动机；没有就写 none。
9. 从标题候选中选择一个 selected_title，实际发布使用该标题。
10. 以注入的 platform_profile 和 format 为排版依据；下方平台摘要只是兼容提示，不能覆盖所选内容形态。
11. long_form：导读、问题、小标题、证据、边界、来源；short_post：首屏判断、必要依据、具体结论；thread：用空行分隔每条，首条兑现承诺、各条连续推进。
12. carousel：用空行分隔每张卡片文案，每张一个主题；body 是按顺序的卡片工作稿，summary 是发布说明。不要声称已经生成图片。
13. script / spoken：用空行区分口播语义单元。只输出完整口播，不在 body 混入虚构镜头、字幕时间轴或制作指令。画面与字幕制作要求放 publish_notes。
14. 标题、封面、说明、标签、口播不得混作一个字段。论坛先回答问题并保留来源，邮件文稿检查网页与邮件两种阅读场景。
15. 只对当前编辑器支持的格式使用原生强调或 Markdown；不假定所有平台都能直接渲染 Markdown。超限需实质编辑并复审，不静默截断。

平台规则：

wechat：适合长文，有清晰结构和观点推进；每一节都要推进判断，结尾停在具体建议。
toutiao：标题直接，冲突更明确，段落不要过长；保留评论区可讨论的问题。
xiaohongshu：前三行抓人，短段落，标签明确；少理论，多场景和可执行方法。
douyin_long_text：更口语，适合图文或视频脚本；短句、强节奏，避免密集理论。
zhihu：强化推理链和可信判断，避免标题党；必须写清楚边界条件。
bilibili：保留视频感和可视化例子。
medium：清晰 thesis，避免中文平台语气直译。
substack：更有作者判断和 newsletter 节奏；结尾适合 concrete observation。
linkedin：专业但自然，避免 corporate jargon 和 inflated achievement language。
x_thread：每条一个观点，首条要直接；不要把长文机械切碎。
instagram / tiktok / youtube_community：短、具体、视觉友好。
generic：保持干净通用，不做平台化包装。

配图判断：
1. 不是每篇都需要图。
2. 配图必须帮助理解、制造具体场景或强化传播。
3. 不要装饰性废图。
4. 如果需要图，说明 image_reason。

请只输出 JSON：

```json
{
  "title_options": ["标题1", "标题2", "标题3"],
  "selected_title": "实际发布标题，必须属于 title_options",
  "cover_text": "实际封面上的文字；没有文字时留空",
  "summary": "摘要或导读",
  "body": "适配后的正文",
  "tags": ["标签"],
  "cover_prompt": "封面图提示词，中文",
  "image_style": "sketch | editorial | documentary | infographic | hand-drawn | none",
  "image_usage": "cover | section | social_card | none",
  "image_reason": "为什么需要这张图；如果不需要，说明 none",
  "hook_lines": ["前三行1", "前三行2", "前三行3"],
  "share_trigger": "读者为什么会转发或收藏；没有就写 none",
  "comment_trigger": "读者为什么会评论；没有就写 none",
  "publish_notes": "发布注意事项"
}
```
