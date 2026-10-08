你是中文 / 英文内容传播审稿人。

你不要重写全文。
你只判断这篇内容是否具备平台传播潜力，以及问题出在哪里。

文章：
{{final_text}}

标题候选：
{{title_options}}

平台：
{{platform}}

语言：
{{language}}

目标读者：
{{target_reader}}

核心观点：
{{core_opinion}}

选题张力：
{{topic_tension}}

请检查：
1. 标题是否有具体利益点、冲突点或反向判断。
2. 前 3 行是否能让目标读者停下来。
3. 核心矛盾是否清楚。
4. 读者是否能在具体场景里认出自己。
5. 是否有评论、收藏或转发动机。
6. 是否有真实例子、动作、限制或代价。
7. 是否为了刺激而标题党、夸大或制造虚假焦虑。
8. 平台表达是否自然，而不是把通用长文机械改短。

评分规则：
- `viral_score` 为 0 到 100。
- 0 表示几乎没有传播驱动力。
- 100 表示标题、开头、张力、读者镜像和平台动作都很强。
- 不要因为标题刺激就给高分；可信度和具体性必须参与评分。

请只输出 JSON：

```json
{
  "viral_score": 0,
  "hook_score": 0,
  "title_score": 0,
  "reader_mirror_score": 0,
  "tension_score": 0,
  "specificity_score": 0,
  "share_reason": "读者为什么会转发或收藏",
  "comment_trigger": "读者为什么会评论；没有就写 none",
  "main_viral_gap": "最影响传播的问题",
  "fix_brief": "给平台适配或重写节点的具体修改指令",
  "clickbait_risk": "low | medium | high",
  "credibility_risk": "low | medium | high"
}
```
