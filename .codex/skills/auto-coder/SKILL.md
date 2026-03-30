---
name: auto-coder
description: Autonomous spec-driven development agent. Syncs DEV_SPEC.md into chapter-based reference files, identifies the next pending task from the schedule, implements code following spec architecture and patterns, runs tests with up to 3 auto-fix rounds, and persists progress with atomic commits. Use when user says "auto code", "自动开发", "自动写代码", "auto dev", "一键开发", "autopilot", or wants fully automated spec-to-code workflow.
---

# Auto Coder

One trigger completes **read spec → find task → code → test → persist progress**.

Optional modifiers: append a task ID (e.g. `auto code B2`) to target a specific task, or `--no-commit` to skip git commit.

---

## Pipeline

```
Sync Spec → Find Task → Implement → Test (≤3 fix rounds) → Persist
```

Pause only at the end for commit confirmation. Run everything else autonomously.

> **⚠️ CRITICAL: Activate `.venv` before ANY `python`/`pytest` command (idempotent, re-run if unsure).**
> - **Windows**: `.\.venv\Scripts\Activate.ps1`
> - **macOS/Linux**: `source .venv/bin/activate`

## Reference Map

All files under `.codex/skills/auto-coder/references/`:

| File | Content | When to Read |
|------|---------|-------------|
| `01-overview.md` | Project overview & goals | First task or when needing project context |
| `02-features.md` | Feature specifications | When implementing feature-related tasks |
| `03-tech-stack.md` | Tech stack & dependencies | When choosing libraries or patterns |
| `04-testing.md` | Testing conventions | When writing tests |
| `05-architecture.md` | Architecture & module design | When creating/modifying modules |
| `06-schedule.md` | Task schedule & status | Every cycle (Sync Spec step) |
| `07-future.md` | Future roadmap | When planning or assessing scope |

---

### 1. Sync Spec

```powershell
python .codex/skills/auto-coder/scripts/sync_spec.py
```

Then read the schedule file to get task statuses:
- Read `.codex/skills/auto-coder/references/06-schedule.md`

Task markers:

| Marker | Status |
|--------|--------|
| `[ ]` / `⬜` | Not started |
| `[~]` / `🔶` / `(进行中)` | In progress |
| `[x]` / `✅` / `(已完成)` | Completed |

---

### 2. Find Task

Pick the first `IN_PROGRESS` task, then the first `NOT_STARTED`. If user specified a task ID, use that directly.

Quick-check predecessor artifacts exist (file-level only). On mismatch, log a warning and continue — only stop if the target task itself is blocked.

---

### 3. Implement

1. **Read relevant spec** from `.codex/skills/auto-coder/references/`:
   - Architecture: `05-architecture.md`
   - Tech details: `03-tech-stack.md`
   - Testing conventions: `04-testing.md`
   - **Reporting rule (mandatory)**: explicitly list what was read from `03-tech-stack.md` (section/topic keywords or matched lines) and explain how each item influenced the subsequent `Extract` / `Plan files` / `Code` decisions.

2. **Extract** from spec: inputs/outputs, design principles (Pluggable? Config-driven? Factory?), file list, acceptance criteria.
   - **Traceability rule (mandatory)**: build a concise mapping checklist before coding:
     - 需求条目/验收点 -> 代码落点(文件/方法) -> 测试落点(用例名)
     - Every key bullet in acceptance criteria must map to both implementation and a verification test.

3. **Plan** files to create/modify before writing any code.

4. **Code** — project-specific rules:
   - Treat spec as single source of truth
   - Use `config/settings.yaml` values, never hardcode
   - Match existing codebase patterns and style

5. **Commenting policy (mandatory)**:
   - **Goal**: comments/docstrings should let another engineer understand **what it does + how it works + key constraints** without reading the whole code path.
   - **Language**: write comment content in Chinese by default (including docstrings), unless the user requests English.
   - **Where to add deeper comments** (required for key paths): factories/routing, protocol handling, config validation, error/fallback handling, parsing/serialization, and any non-obvious algorithm.
   - **Docstring depth rule (enforced)**:
     - For **关键/复杂/较长** public methods (factory `create`, provider `chat/embed`, validation, fallback paths): use structured Chinese docstrings with `Args`/`Returns`/`Raises`/`Example` when helpful, and explicitly cover:
       - 做什么：该方法在当前流程中的职责与输出结果。
       - 为什么：为何采用当前实现路径，而不是更直观的替代方案。
       - 关键权衡：性能/可维护性/扩展性/成本上的主要取舍。
       - 失败路径：异常、降级或回退策略，以及对调用方的可见行为。
     - For simple helpers: short Chinese docstrings/comments are fine.
   - **Complex method docstring template (copyable)**:

```python
"""<一句话职责：该方法在流程中的位置与输出>

做什么：
- <核心职责 1>
- <核心职责 2>

为什么：
- <选择当前实现路径的原因>

关键权衡：
- <性能/可维护性/扩展性/成本上的取舍>

失败路径：
- <异常或降级条件>
- <对调用方可见行为：抛错/回退/默认值>

Args:
    <param>: <含义、格式、边界条件>

Returns:
    <返回值语义与关键字段>

Raises:
    <异常类型>: <触发条件>

Example:
    >>> <最小可运行调用示例>
"""
```

   - **Template usage notes**:
     - 复杂方法至少填写“做什么/为什么/关键权衡/失败路径”四段；`Args`/`Returns`/`Raises`/`Example`按需补齐。
     - 若方法包含降级逻辑，`失败路径`必须写清“何时降级”与“降级后的行为契约”。
   - **Method summary must include** (when not trivial):
     - 用途（解决什么问题/在流程中处于哪一段）
     - 方法（核心步骤/核心数据结构/关键假设）
     - 关键约束（输入 shape、边界条件、错误策略、性能/成本考虑）
   - **Error comments**: when raising/wrapping exceptions, explain why this error is surfaced and what information is intentionally hidden (e.g., sensitive config).
   - **Avoid**: line-by-line restating obvious code; prefer explaining *why* and tradeoffs.
   - **Self-review checklist (comments)**: before tests, verify key paths have enough explanation for fast onboarding.
6. **Write tests** alongside code:
   - Place in `tests/unit/` or `tests/integration/` per spec
   - Mock external deps in unit tests
   - **Test annotation rule (mandatory)**: every `test_*` method must include a Chinese docstring/comment that states **测试目标 + 场景输入 + 预期行为/验收点** so readers can quickly understand what is being validated.
   - **Test comment style (mandatory)**: each `test_*` docstring must use a multi-line `Given/When/Then` (or “前置/动作/断言”) structure; do not compress all three parts into one line.

7. **Self-review** before running tests:
   - Verify all planned files exist and tests import correctly.
   - Verify comment coverage on key logic is sufficient for fast onboarding/readability.
   - Verify the 需求 -> 代码 -> 测试 mapping checklist is complete and each acceptance bullet has an executable test assertion path.

---

### 4. Test & Auto-Fix

```

Round 0..2:
  Run pytest on relevant test file
  If pass → go to step 5
  If fail → analyze error, apply fix, re-run

Round 3 still failing → STOP, show failure report to user
```

---

### 5. Persist

1. **Update `DEV_SPEC.md`** (global file): change task marker `[ ]` → `[x]`
2. **Re-sync**: `python .codex/skills/auto-coder/scripts/sync_spec.py --force`
2.5. **Update docs (optional)**:
   - Only update `docs/notes/decisions.md` / `docs/notes/faq.md` when user explicitly requests it.

2.6. **Implementation report (mandatory, user-visible)**:
   - Before `Show summary & ask`, output a full **Implement 1/4 ~ 4/4** report to the user.
   - Do not collapse this into a short paragraph.
   - Required structure:

```
Implement 1/4 (Read spec)
- Exact files read
- What was read from `03-tech-stack.md` (keywords / matched lines)
- How each item influenced `Extract` / `Plan files` / `Code`

Implement 2/4 (Extract + mapping checklist)
- Requirement/acceptance -> code location (file/method) -> test case mapping
- Mark each mapped item as planned/done

Implement 3/4 (Plan files)
- Files to create/modify (with purpose)
- Why each file change is necessary

Implement 4/4 (Code)
- What was actually changed
- Commands run and outcomes
- Deviations/fixes applied during implementation
```

   - **Non-compliance rule**: if this detailed report is missing, the run is incomplete even if code/tests passed.

3. **Show summary & ask**:

```
✅ [A3] 配置加载与校验 — done
   Files: src/core/settings.py, tests/unit/test_settings.py
   Tests: 8/8 passed
   Commit: feat(config): [A3] implement config loader

   "commit" → git add + commit
   "skip"   → end
   "next"   → commit + start next task
```

On "next", loop back to step 1 and start the next task.














