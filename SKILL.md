---
name: midnight-advertorial
description: Detects, explains, rewrites, and generates low-AI-feel Chinese or English content. Use for lowering AI feel, checking template-like drafts, collecting writing briefs, generating drafts, platform adaptation, Markdown delivery, account/platform/style management, configurable output directories, browser draft filling, and API/browser/mock publication status collection.
---

# midnight advertorial Skill

## Purpose

### Account content management

For account/platform/style configuration, output directories, opening and filling editor pages, or collecting publication status, read `docs/account-content-management.md`. Start the local manager with `python -m scripts.manage_content --open`, or use `scripts.run_skill.py --binding` with an imported account configuration. Keep Account → PlatformBinding → StyleProfile → ContentVersion → Publication → StatusSnapshot identities separate.

Configuration and export precedence is task → platform binding → account → manager default; style fields use task → selected preset. Task facts never come from style samples. Store each version in its own account/platform/content/version directory, retaining the complete publication, resolved input and style digest. A generated draft still requires human review.

One-click browser tasks require the installed `browser-helper/` extension, the correct logged-in account and verified page mappings. Read `docs/browser-helper.md` before configuring actual platform selectors. The first three browser hosts are WeChat Official Account, Toutiao and Xiaohongshu. Preflight identity/fields, preserve existing drafts, read back after fill, and stop before save/submit/publish. Unsupported rich editors and media uploads remain explicit failures; mock fill is not real platform validation.

Publication collection supports api/browser/mock with observed timestamps, query failures, preserved last success and configurable polling. API/mock polling runs in the local service; browser polling only dispatches while the manager page is visible and the user is not editing. Only verified account/content identities may produce a real snapshot. Mock results remain labelled and do not enter real publication feedback automatically. Unknown or stale values stay visible, missing metrics are null, and neither association nor fill proves publication. Do not create Codex automations or publish externally as part of this management workflow.

### End-to-end production routing

When asked for an article, advertorial, image-text deliverable or video, read `references/content-production-pipeline.md` and record the task using `templates/content-production-task.md`. Select the production medium and commercial status separately: promotional articles, cards and videos all require commercial claim/disclosure review. Follow shared brief/evidence/strategy/copy stages, then the relevant production branch, artifact review, delivery and authorized publication/feedback.

This is an assisted operating procedure, not an implemented media or publishing engine. Record actual evidence at each stage. Never treat prompts/cards/scripts as rendered media, generated files as reviewed artifacts, ready_for_human_review as human approval, or delivery as publication. Unsupported steps remain manual or pending. Publication and paid media generation require applicable authorization; task planning does not grant it. Read the detailed reference only for the requested branch and common gates.

### Platform layout routing

For domestic or international adaptation, load `rules/platform_layouts.json` and consult `rules/platform-formatting-guide.md`. The catalog covers 34 platform/content entries (15 domestic, 16 international, 3 general). Select both the platform and content format before writing; a video script, caption, carousel, thread and article are different deliverables. Supported formats are `long_form`, `short_post`, `carousel`, `thread`, `script`, `spoken`, `text`, subject to each profile's formats.

Use each profile's content order, paragraph method, emphasis method, media method and native publishing steps. Keep title, cover text, summary, body and tags separate. Separate carousel cards, thread posts and script units with blank lines. Preserve facts, sources and qualification; do not silently truncate to fit. Never claim Markdown universally renders, fabricated timestamps are real, generated card text is an image, or recommended lengths predict reach. Check current account limits and native previews before publication.

The local runner exposes source-preserving `platform_output.layout_plan.blocks` and publishing instructions; semantic adaptation remains `not_evaluated`. The model workflow injects the same catalog and checks format fit in editorial review, regenerating the layout after repair. Neither mode automatically publishes or proves native rendering.

This skill detects, explains, and reduces AI-like writing patterns in Chinese or English content. It is designed for publishing workflows such as WeChat Official Account, Toutiao, Xiaohongshu, Douyin image-text scripts, Bilibili, Zhihu, blogs, Medium, Substack, LinkedIn, X/Twitter threads, Instagram captions, TikTok scripts, YouTube Community posts, SEO/GEO content, and AI-generated drafts.

The skill must not simply replace banned words. It must evaluate structure, rhythm, specificity, author judgment, examples, tone, and platform fit.

Core principle:

> Fix structure first, language second, and only then polish wording.

Expanded principle:

> Build tension before structure, fix structure before language, and only then polish wording.

This skill can use selected ideas from viral long-form writing systems, but it must keep credibility above stimulation. The goal is not to hijack attention. The goal is to make the draft specific, accountable, and worth reading.

Execution modes:

- `strict_model_workflow`: model text workflow with topic tension, candidate comparison, structure, drafting, rule scan/Judge, bounded rewriting, platform formatting, final editorial review/repair, and Viral Judge; output awaits human review. It does not execute media production or publish content.
- `local_deterministic`: local fallback used by `scripts/run_skill.py`; it performs normalization, deterministic rule scan, lightweight cleanup, heuristic Viral Judge, platform formatting, and Markdown output. It must not be treated as a full AI Judge/Rewriter pass.

---

## When to use this skill

Use this skill when the user asks to:

- 降低 AI 味
- 去掉 AI 感
- 检查 AI 写作痕迹
- 优化公众号文章
- 优化头条文章
- 优化小红书文案
- 把 AI 初稿改得更像人写
- 检测文章是否模板化
- 输出内容质检报告
- 生成发布前审稿清单
- 将内容适配到不同平台
- 采集写作需求并生成可发布文章
- 生成中文、英文或中英双语内容
- 按平台分别配置语言、语气和输出格式

---

## Intake workflow

When a user starts a writing or rewriting request, collect enough information to fill the input contract. If the user already provides most fields, normalize them silently. If key fields are missing and cannot be inferred, ask at most 3 concise questions before writing.

Minimum fields needed to proceed:

- `title`
- `content_goal`
- `platform`
- `language`
- `target_reader`

Optional but recommended fields:

- `raw_material`
- `core_opinion`
- `tone`
- `forbidden_style`
- `personal_examples`
- `platform_configs`
- `style_template`
- `output_dir`

When the user wants a fresh article or a major rewrite, also infer or ask for:

- core tension
- target reader scene
- counter-position
- preferred style template

If the user only gives a topic, make reasonable defaults and mark missing material as a risk. Do not block unless the topic, audience, platform, and language are all unclear.

Example intake object:

```json
{
  "title": "如何去掉 AI 写作味",
  "platform": "wechat",
  "target_reader": "公众号和头条内容创作者",
  "content_goal": "输出一篇低 AI 味、可发布的文章",
  "raw_material": "这里放原始文章、素材或 AI 初稿",
  "core_opinion": "AI 味不是词的问题，而是结构、语气和判断的问题",
  "tone": "直接、实用、有经验感，不要营销腔",
  "forbidden_style": "不要宏大开头，不要结尾升华，不要过度列表化",
  "personal_examples": "可以结合公众号、头条、小红书分发场景",
  "language": "zh",
  "max_rounds": 2,
  "pass_score": 25
}
```

---

## Input contract

Editorial context fields:

- `author_samples`: array of actual author excerpts. Use for voice and rhythm only; their experiences are not facts for a new article.
- `facts`: array of `{id, claim, source}`. IDs must be unique. Source metadata is supplied evidence, not proof of independent verification.
- `forbidden_claims`: array of claims the author does not permit.
- `review_thresholds`: optional `style_min_score`, `expression_min_score`, `distribution_min_score`, `viral_min_score` (0-100).
- `style_guidance`: template/voice text supplied to n8n; local runner reads named or file-based templates and returns their text. Local mode preserves tone requirements but does not perform semantic tone rewriting.

Use `rules/editorial_rules.json` as initial thresholds. They are uncalibrated. Unknown dimensions require human review; factual failures cannot be offset by a strong title score.

The skill accepts a JSON-like object:

```json
{
  "title": "文章标题或主题",
  "platform": "wechat | toutiao | xiaohongshu | douyin_long_text | zhihu | bilibili | baijiahao | kuaishou | juejin | medium | substack | linkedin | x_thread | instagram | tiktok | youtube_community | blog | seo_article | generic",
  "language": "zh | en | bilingual",
  "target_reader": "目标读者",
  "content_goal": "内容目标",
  "raw_material": "原始素材或 AI 初稿",
  "core_opinion": "核心观点",
  "tone": "目标语气",
  "forbidden_style": "禁用风格",
  "personal_examples": "可使用的个人案例",
  "style_template": "风格模板名称或模板文件路径",
  "output_dir": "Markdown 输出目录，可选；默认项目根目录",
  "platform_configs": {
    "wechat": {
      "language": "zh",
      "tone": "直接、实用、有经验感",
      "format": "long_form"
    },
    "linkedin": {
      "language": "en",
      "tone": "clear, practical, experienced",
      "format": "short_post"
    }
  },
  "max_rounds": 2,
  "pass_score": 25
}
```

Required fields:

- `title`
- `content_goal`

Conditionally required fields:

- `raw_material` is required for rewrite, audit, and AI-slop-cleaning tasks.
- `raw_material` is optional for fresh article generation.
- `core_opinion` is strongly recommended. If missing, state the inferred angle before drafting.

Default values:

- `platform`: `generic`
- `language`: `zh`
- `target_reader`: `中文内容读者`
- `content_goal`: `输出一篇低 AI 味、可发布的文章`
- `tone`: `直接、清晰、有经验感，不要营销腔`
- `forbidden_style`: `不要宏大开头，不要结尾升华，不要过度列表化，不要 AI 套话`
- `output_dir`: current project root
- `max_rounds`: `2`
- `pass_score`: `25`

---

## Platform and language configuration

The skill must support single-platform, multi-platform, and per-platform language output.

Rules:

- `language: zh` generates Chinese content.
- `language: en` generates English content.
- `language: bilingual` generates both Chinese and English versions.
- `platform_configs` overrides global `platform`, `language`, `tone`, and `format` for each platform.
- If one platform is configured for Chinese and another for English, create separate Markdown files unless the user asks for one combined file.
- Keep idiom native to the target language. Do not translate Chinese internet phrasing literally into English.
- For bilingual output, write separate sections: `## 中文版` and `## English Version`.
- Platform-specific titles, summaries, tags, and cover prompts should match the configured language for that platform.

Supported platform families:

- Domestic long-form: `wechat`, `toutiao`, `zhihu`, `baijiahao`, `bilibili`, `juejin`, `blog`, `seo_article`
- Domestic short-form: `xiaohongshu`, `douyin_long_text`, `kuaishou`
- International long-form: `medium`, `substack`, `linkedin`, `blog`, `seo_article`
- International short-form: `x_thread`, `instagram`, `tiktok`, `youtube_community`
- Fallback: `generic`

---

## Style template workflow

Before writing, check for style templates in the project root or the user-specified directory.

Default filenames to look for:

- `风格模板.md`
- `style-template.md`
- `style-templates.md`
- `writing-style.md`

Also check the built-in `styles/` directory for reusable templates:

- `practical-essay.md`
- `personal-commentary.md`
- `sharp-opinion.md`
- `xiaohongshu-note.md`
- `linkedin-operator-note.md`

If a matching template exists:

- Read it first.
- Use only the relevant style section requested by `style_template`; if none is requested, choose the closest fit based on platform, language, audience, and topic.
- Preserve the user's core opinion over template language.

If no style template exists and the user requests template-based writing:

- Generate a Markdown style template file in the project root named `风格模板.md`.
- Include several reusable styles for both Chinese and English content.
- After creating the template, use the best-matching style for the current article.

The generated style template should include at least:

- `纪实克制`
- `评论随笔`
- `实用拆解`
- `口语短文`
- `深度长文`
- `Practical Essay`
- `Personal Commentary`
- `Founder/Operator Note`

## Output contract

Return:

```json
{
  "ok": true,
  "execution_mode": "strict_model_workflow | local_deterministic | manual",
  "execution_note": "",
  "job_id": "",
  "title": "",
  "platform": "wechat",
  "language": "zh",
  "status": "ready_for_human_review | needs_human_review | failed",
  "ai_slop_score": 0,
  "pass_score": 25,
  "round": 0,
  "main_problem": "",
  "issues": [],
  "rewrite_brief": "",
  "final_text": "",
  "rule_scan": {},
  "judge_result": {},
  "viral_judge_result": {},
  "content_context": {},
  "candidate_comparison": {},
  "editorial_review": {},
  "platform_output": {
    "title_options": [],
    "summary": "",
    "body": "",
    "tags": [],
    "cover_prompt": "",
    "publish_notes": "",
    "files": []
  },
  "human_review_checklist": []
}
```

When the user asks to generate an article or platform-ready draft, write the final result to a Markdown file by default.

- Default output directory: the current project root.
- If the user specifies a directory, write the Markdown file there instead.
- Use a clean Chinese filename derived from the title, and avoid punctuation that is unsafe for filenames.
- For English files, use a clean kebab-case English filename derived from the title.
- For multi-platform or bilingual output, include platform and language in filenames when needed, for example `如何去掉AI写作味-wechat-zh.md` or `remove-ai-writing-feel-linkedin-en.md`.
- The Markdown file should contain the title as `# ...`, followed by the final article body.
- In the chat response, briefly report the file path and any important review notes. Do not paste the full article again unless the user asks.

---

## Workflow

### Step 1: Collect and normalize input

Collect missing brief fields when needed, then normalize the incoming content and fill missing defaults. Do not invent a core opinion silently; if it is missing, infer a tentative angle and label it as inferred. If the material is too sparse, mark this as a risk.

### Step 1.5: Load or create style template

Collect author samples, supplied facts and forbidden claims first. Preserve their provenance in `content_context` throughout planning, writing, rewriting and review. Mark missing material rather than inventing it.

Look for a style template in the project root or requested output directory. If found, use it. If not found and template-based writing is requested, generate `风格模板.md` in the project root and then use the closest matching style.

### Step 1.75: Topic tension planning

Before structure planning, decide whether the topic has enough reading tension.

Use `prompts/00_topic_tension_planner.md` and `rules/topic_tension_rules.json`.

Check:

- core tension
- reader mirror
- counter-position
- sharper angle
- emotional trigger without manipulation
- timeliness hook
- evidence to collect
- angles to avoid

If the topic is weak, do not compensate with exaggerated language. Narrow the angle, make the reader scene more concrete, or mark missing material as a risk.

Recommended structure templates:

- `conflict_breakdown`: concrete scene -> counterintuitive judgment -> misconception -> real cause -> accountable takeaway
- `identity_mirror`: reader situation -> shared confusion -> author judgment -> concrete example -> grounded close
- `opinion_reversal`: common view -> disagreement -> why it is wrong -> better framing -> action advice
- `experience_review`: lived event -> earlier mistake -> later understanding -> method -> boundary

### Step 2: Structure planning

Before planning the structure, use `prompts/08_candidate_comparison.md` to generate three distinct angle/title/opening candidates and compare every pair. Record promises, fact IDs, selection and reasons. Use the selected candidate for the structure and initial draft. Do not treat this editorial selection as a published A/B test. The local deterministic runner does not generate or compare candidates.

Analyze or generate the article structure before writing or rewriting.

Check:

- generic opening
- generic ending
- symmetrical sections
- excessive headings
- lack of author judgment
- weak examples
- over-explained concepts
- forced inspirational conclusion
- weak topic tension
- vague reader mirror
- no counter-position
- no evidence plan

Return a structure plan, not the full article.

### Step 3: Draft generation

Generate a first draft only when the user wants rewriting or when raw material is available.

Rules:

- Do not add generic openings.
- Do not add generic endings.
- Do not invent facts.
- Do not over-polish.
- Preserve the user's core opinion.
- Prefer concrete scenes, constraints, and judgment.

### Step 4: Rule scan

Run deterministic checks before model judgment.

Detect:

- banned phrases
- meta phrases
- repeated sentence starts
- paragraph symmetry
- list overuse
- generic opening
- generic ending

Generate a rule-based score.

### Step 5: AI Judge

Use a model as a reviewer. The judge must not rewrite the article.

It should return:

- `ai_slop_score`
- `verdict`
- `main_problem`
- issue list
- evidence
- fix suggestions
- `rewrite_brief`

### Step 6: Targeted rewrite

Rewrite only according to the judge result.

Do not:

- change the core opinion
- invent examples
- add fake data
- make the text more generic
- overuse lists
- end with empty inspiration

### Step 7: Second scan

Run rule scan and AI Judge again.

If `score <= pass_score`:

- send to final human review

If `score > pass_score` and `round < max_rounds`:

- rewrite again

If `score > pass_score` and `round >= max_rounds`:

- mark as `needs_human_review`

### Step 8: Platform formatting preparation

Format the article and generate title candidates using `prompts/05_platform_formatter.md`. The next step must judge these actual candidates and the adapted body.

### Step 9: Viral Judge

Before Viral Judge, use `prompts/09_editorial_review.md` on the actual adapted draft. Return four independent dimensions: facts, style, expression and distribution. Include quoted evidence, claim-to-source mappings, missing evidence and actionable fixes. Use null scores for unknown dimensions. Without author samples, style remains unknown. Do not call blacklist matches authorship detection.

All dimensions must pass their configured gates to be ready for human review. An unknown or failed dimension requires review even if the overall AI-slop score is low. This final review happens after platform formatting to catch factual changes introduced during adaptation.

A pass verdict with unresolved issues or a null score is not accepted as a pass. Review the complete visible publication: selected title, cover text, summary, body, hook_lines and tags. Final editorial repair must return a complete publication object with refreshed metadata; missing required fields or invalid types require review instead of partial acceptance. Local final_text is the adapted body actually exported. Invalid platform/language/format settings and non-integer round limits must fail explicitly rather than silently routing to generic content.

Choose `selected_title` from the actual platform candidates and review it together with body and cover text. Explicit fixable final-review issues enter the editorial rewrite loop and repeat deterministic scanning and four-dimensional review. Initial and editorial rewrites share `max_rounds`. Unknown evidence without actionable issues goes to human review. Parsing failures return a structured stage error through the normal response path.

Local mode always returns `needs_human_review` because semantic fact and voice checks remain unevaluated.

Use `prompts/07_viral_judge.md`, `rules/viral_rules.json`, and `schemas/viral_judge.schema.json`.

The Viral Judge must not rewrite the article. It should evaluate:

- title strength
- first-three-line hook
- core tension
- reader mirror
- specificity
- share reason
- comment trigger
- clickbait risk
- credibility risk

If the viral score is weak, do not add hype. Return a `fix_brief` that strengthens the reader scene, title promise, concrete evidence, or platform-specific opening.

### Platform formatting rules

Format the final text for the target platform.

The n8n workflow handles one platform and one language (`zh` or `en`) per request. After adaptation and editorial review/repair, run the model Viral Judge on the actual publication title, cover text and adapted body, not unused title alternatives. Malformed review output, a viral score below the configured minimum, or high credibility/clickbait risk requires human review. Viral scores describe editorial signals, not guaranteed reach.

Platform rules:

#### wechat

- deeper structure
- stronger introduction
- clear section flow
- can keep moderate long-form reasoning
- suitable for article publishing
- each section should advance the judgment
- ending should stop at a concrete judgment or next step

#### toutiao

- stronger conflict
- more direct title
- avoid overly academic paragraphs
- add comment-worthy angles
- keep the debate grounded in evidence

#### xiaohongshu

- shorter paragraphs
- practical tone
- stronger first 3 lines
- tags required
- fewer theories, more scenes and actions
- no fake intimacy

#### douyin_long_text

- oral rhythm
- useful for image-text or video scripts
- avoid dense paragraphs

#### zhihu

- stronger reasoning chain
- credible personal or professional judgment
- avoid clickbait and empty debate framing
- state boundary conditions

#### bilibili

- suitable for video intro, column, or community post
- conversational but not chaotic
- keep examples easy to visualize

#### medium

- clear thesis
- narrative or essay-like flow
- avoid translated Chinese platform tone

#### substack

- personal authority and point of view
- newsletter rhythm
- can include a sharper closing observation
- close with a concrete observation, not inspiration

#### linkedin

- professional but human
- concise paragraphs
- avoid corporate jargon and inflated achievement language
- emphasize decisions, tradeoffs, and accountable examples

#### x_thread

- one idea per post
- strong opening post
- maintain continuity across thread items
- do not split a long article mechanically

#### instagram / tiktok / youtube_community

- short, direct, visual-friendly
- keep hooks concrete
- avoid generic motivational endings

#### generic

- keep a clean, reusable version
- avoid platform-specific hooks

---

## Chinese AI Slop signals

### Banned phrase families

Use `rules/zh_blacklist.json` as the default list.

Examples:

- 在当今时代
- 随着技术不断发展
- 信息爆炸的时代
- 不难发现
- 值得注意的是
- 赋能
- 闭环
- 新范式
- 底层逻辑
- 深度融合
- 全面提升
- 高效协同
- 未来可期
- 降本增效
- 打破边界
- 重塑格局
- 显著提升
- 极具价值
- 革命性
- 颠覆式

### Meta phrases

Use `rules/zh_meta_phrases.json` as the default list.

Examples:

- 接下来我们将
- 本文将探讨
- 通过以上分析
- 综上所述
- 总而言之
- 在上一节中
- 我们已经了解了
- 本节将

## Writing tension and anti-slop depth

Use three layers of defense:

1. Surface: remove banned phrases, meta phrases, fake polish, and platform-inappropriate formatting.
2. Middle: add concrete scenes, personal judgment, real constraints, and examples.
3. Deep: make sure the article has a non-template point of view that another generic AI draft would not easily reproduce.

Deep checks:

- Does the article have one accountable judgment?
- Are examples specific to scene, action, and constraint?
- Could this paragraph be moved to another topic unchanged?
- Are there impressive-sounding sentences that do not require the author to stand behind them?
- Did the rewrite merely become smoother, or did it become more specific?

## Visual prompt workflow

Use visuals only when they help comprehension or platform performance.

Return visual fields in `platform_output`:

- `cover_prompt`
- `image_style`
- `image_usage`
- `image_reason`

Rules:

- Do not add decorative visuals just to fill a slot.
- Covers should express the core tension, reader scene, or concrete outcome.
- Use `none` for image fields when text-only is better.
- Match visual style to platform and topic.

Suggested styles:

- `editorial`: professional content, essays, LinkedIn, WeChat.
- `documentary`: realistic scenes, short video/image-text scripts.
- `hand-drawn`: Xiaohongshu or lighter social notes.
- `infographic`: technical, SEO, concept comparison, Zhihu.
- `sketch`: reflective essays or philosophical topics.

## Feedback memory

Record publication snapshots with `python -m scripts.editorial input.json`. The default append-only log is `feedback/publication_metrics.jsonl`; `--log` selects another file. See `examples/publication_feedback.json` (synthetic data).

Each record identifies job, platform, variant, timezone-aware publication and observation-end timestamps, experiment design and available metrics. Missing denominators or zero exposure produce null rates. Randomized records require an experiment ID; a sequential title change is observational. Do not declare a winner or update thresholds automatically.

Calibration: build balanced human-reviewed examples of good drafts, weak drafts and false positives. Preserve model/prompt versions and independent human labels. Use held-out examples to compare fact errors, style agreement, expression and distribution judgments. Publish observations can inform hypotheses, but do not prove that a prompt change caused a result.

Run `python -m scripts.calibrate_reviews review_labels.jsonl` to compare paired human/model four-dimensional verdicts on held-out records. Include id, model_version, prompt_version, human_reviewer and split. The report includes agreement, false passes, false rejections and unknown disagreements, with version groups. It does not alter thresholds. Count metrics in publication feedback must be integers; watch_seconds may be fractional.

Use `feedback/content_feedback_log.jsonl` for lightweight feedback accumulation before adding a complex RLHF system.

Each feedback line can contain:

```json
{
  "title": "",
  "platform": "",
  "task_type": "rewrite | generate | adapt",
  "score": 1,
  "liked": ["开头具体", "观点清楚"],
  "disliked": ["结尾偏虚"],
  "rules_to_strengthen": ["specific_opening", "concrete_ending"]
}
```

Do not automatically rewrite rules from one feedback item. Use accumulated feedback to adjust style templates, platform rules, and review checklists.

---

## Scoring

Use both rule score and judge score.

Final score:

```text
overall_score = max(rule_score, judge_score)
```

Score levels:

```text
0 - 25     pass
26 - 45    light rewrite
46 - 70    heavy rewrite
71 - 100   restructure required
```

---

## Human review checklist

Before final delivery, check:

1. Is the core opinion clear?
2. Is the opening specific?
3. Can the first paragraph be used in another article? If yes, rewrite it.
4. Are there empty adjectives?
5. Are the examples real?
6. Does the ending stop at a concrete judgment?
7. Does the article sound like the author would actually say it?
8. Are facts, numbers, and claims verifiable?
9. Is the platform format suitable?
10. Does the article still feel over-polished?
11. Is there a clear topic tension?
12. Can the target reader see themselves in a concrete scene?
13. Is the counter-position clear and fair?
14. Did the draft gain specificity rather than just smoother wording?
15. Does the visual prompt serve the content instead of decorating it?
16. Does the title promise match the body?
17. Do the first 3 lines create real reader recognition?
18. Is the share/comment trigger credible rather than manufactured?

---

## Final rule

Do not make the article merely smoother.

Make it more specific, more grounded, and more accountable.
