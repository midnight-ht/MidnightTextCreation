# Test: Blacklist

Input:

```text
在当今时代，AI 正在全面赋能内容创作，并形成新的闭环。
```

Expected:

- blacklist_hits should include 在当今时代
- blacklist_hits should include 赋能
- blacklist_hits should include 闭环
- score should be greater than 0
