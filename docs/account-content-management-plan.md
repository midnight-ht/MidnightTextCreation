# Account Content Management Implementation Plan

> Execute tasks in the current session with test-driven-development; browser helper implemented under subagent-driven-development. No Git repository exists, so no worktree or commit operations apply.

Goal: Account/platform/style configuration, isolated content exports, local manager, one-click browser tasks and API/browser/mock status collection.
Architecture: Python standard-library SQLite service and local HTML UI, existing deterministic runner, MV3 browser helper. Runtime files stay under configurable data/output paths; snapshots and task errors never become publication approval.
Spec: account-content-management-design.md

## Tasks

- [x] Configuration and content persistence: scripts/content_manager.py, tests/test_content_manager.py. Validate unique IDs/references/platform formats, resolve override precedence and paths, run_single into version directories; persist immutable publication bundle and support imports. Exercise restart, two accounts, collision/escape and invalid references.
- [x] Collection and tasks: scripts/publication_status.py plus manager task methods, status tests. Real HTTP adapter validates identity/error/time/metrics, mock source never promotes to real; browser task queue binds exact account and version. Preserve last good snapshot on errors and separate transport/business states.
- [x] Service and UI: scripts/manage_content.py and manager/index.html/app.js/style.css, tests/test_manager_http.py. Local-only authenticated mutations, CRUD config, export/import, content generation/import, fill/collect task completion, publication association, configurable polling with backoff/stop. Test full request cycle on ephemeral localhost server and unsafe Origin/Host.
- [x] Browser helper: browser-helper/ + tests/test_browser_helper.cjs. One-click bridge, page opening, identity checks, draft preservation, field fill/readback and published identity/status collection; configured adapters remain unverified until live platform validation.
- [x] Integration/docs: examples/account_config.json, schemas/management.schema.json, README/SKILL/manifest and task template. Add account CLI binding without breaking existing input. Run existing Python/Node checks, new tests and UI demo; report real-platform validation separately.

Each task: add failing tests → run RED → implement → run GREEN → review observed behavior. No external publishing or account changes.

Ruling: A helper extension executes local manager browser tasks because persistent local service cannot call Codex browser tools autonomously. Costs: user must load extension into their logged-in browser; configured real mappings require live validation.

Execution notes: Real platform login/selector/media acceptance remains pending. API adapter verified against a local HTTP service, not platform production APIs. Existing editorial feedback remains a separate manual tool; manager snapshots are not automatically promoted. Local manager smoke verified content generation, version export, simulated association/collection and persistence across restart.
