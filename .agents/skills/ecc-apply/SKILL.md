---
name: ecc-apply
description: "Token-lean router for applying ECC (Everything Claude Code) inside DeepSeek Harness: given a task, pick the right ECC workflow family and exact .agents/workflows/<cmd>.md shim, with run-order and stop condition, then apply it with minimal reads. TRIGGER when the user invokes /ecc-apply with a task (e.g. 'fix a bug', 'build MVP', 'PRD to PR'), or says 'which ECC workflow for X', 'orient me for X', 'apply the ECC flow for X', 'chạy theo quy trình ECC cho X', 'định hướng theo ECC'. DO NOT TRIGGER when the user wants the task done directly without ECC ceremony, wants deep docs for ONE command (use ecc-guide), wants the full catalog listing (use ecc-recipes), or wants a prompt rewritten (use prompt-optimizer)."
argument-hint: <task description | empty=list families>
origin: local
author: user (adapted from ecc-guide for DSH)
metadata:
  version: "1.0.0"
---

# ECC Apply — token-lean ECC router for DeepSeek Harness

One entry point: when the user names a task and wants ECC to *orient* the work,
decide **which ECC workflow family + exact command shim applies, in what order,
and when to stop** — then apply it inside DSH spending the fewest tokens.

Adapted from `ecc-guide` (navigate ECC parts) + `ecc-recipes` (family + run-order
+ stop condition), rebuilt for this DSH environment where `.agents/workflows/*.md`
are **reference shims only** — DSH does not auto-load them as slash commands, so
the agent executes them manually.

## Environment facts (this repo — hardcoded, do not re-derive)

- ECC config root: `.agents/` at repo root.
  - `.agents/workflows/*.md` — **94 command shims** (ECC slash-commands).
  - `.agents/rules/*.md` — language/harness rules (e.g. `python-fastapi.md`,
    `agent-force-update-safety.md`). Loaded as project guidance.
  - `.agents/skills/*/SKILL.md` — DSH **auto-loads** these skills.
- DSH skill format = single `SKILL.md` with YAML frontmatter (`name`,
  `description`, `argument-hint`, `origin`, `author`, `metadata.version`).
- DSH tooling to use: `glob` (list files), `grep` (search), `read` (with
  `limit`/`offset`). No bash `find`/`rg` needed.

## When to Activate

- User names a task and wants ECC orientation: `/ecc-apply fix bug trong agent`,
  `/ecc-apply build mvp`, `/ecc-apply prd to pr`, "chạy theo quy trình ECC".
- User asks which ECC workflow family matches a task, and how to apply it.

## Do Not Use When

- Task should be done directly with no ECC ceremony (execute, don't route).
- Deep docs for one command — point to `ecc-guide` / the workflow file itself.
- Full catalog dump — that is `ecc-recipes` catalog mode.

## Family table (94 commands, live in `.agents/workflows/`)

Match the task by family first; then pick the exact shim. **Never re-list the
directory** — this table is the source of truth (verified 2026-08).

| Family | Members (this repo) | Task it fits | Typical run-order |
|---|---|---|---|
| `orch-*` | orch-build-mvp, orch-add-feature, orch-change-feature, orch-fix-defect, orch-refine-code, orch-review | one scoped task: build MVP / add / change / fix defect / refine / review | pick one by task kind; runs internal phases |
| `prp-*` | prp-prd, prp-plan, prp-implement, prp-commit, prp-pr | PRD → plan → implement → commit → PR | prp-prd → prp-plan → prp-implement → prp-commit → prp-pr |
| `epic-*` | epic-decompose, epic-claim, epic-validate, epic-review, epic-unblock, epic-sync, epic-publish | large multi-unit epic, parallel units | decompose → claim → validate → review → unblock → sync → publish |
| `multi-*` | multi-plan, multi-execute, multi-workflow, multi-backend, multi-frontend | multi-model workflow | multi-plan → multi-execute → review (or multi-workflow) |
| `loop-*` | loop-start, loop-status | managed autonomous loop | loop-start `<pattern>` then loop-status |
| `gan-*` | gan-build (code), gan-design (UI) | generator + evaluator loop | self-looping; add max-iteration backstop |
| `hookify-*` | hookify, hookify-list, hookify-configure, hookify-help | behavior-hook management | hookify → hookify-list → hookify-configure |
| learning | learn, learn-eval, evolve, promote, prune, instinct-status, instinct-export, instinct-import | continuous-learning / instincts | learn → instinct-status → evolve → promote |
| lang triads | cpp/go/rust/kotlin/flutter/react: `-test`, `-build`, `-review`; gradle-build; fastapi-review, python-review, vue-review | per-language TDD → fix → review | `<lang>-test` → `<lang>-build` → `<lang>-review` |
| singletons | plan, plan-prd, plan-canvas, pr, code-review, review-pr, checkpoint, build-fix, feature-dev, refactor-clean, project-init, projects, sessions, save-session, resume-session, santa-loop, quality-gate, security-scan, test-coverage, update-codemaps, update-docs, auto-update, aside, cost-report, ecc-guide, harness-audit, jira, marketing-campaign, model-route, pm2, setup-pm, skill-create, skill-health | standalone or glue between groups | single-shot |

## How to apply (token-lean steps)

1. **Match family** from the table — 1 line, no directory listing.
2. **Confirm the shim exists**: `glob .agents/workflows/<cmd>.md` (skip if the
   table already lists it — table was verified live).
3. **Head-read only**: `read .agents/workflows/<cmd>.md` with `limit: 40` to
   confirm purpose + phases. Do NOT read the whole file unless a phase is unclear.
4. **Find stop condition cheaply**: `grep` the shim for
   `STOP|done|complete|exit|criteria|acceptance` (ripgrep regex).
5. **Rules check (optional)**: `glob .agents/rules/*<stack>*` and read only
   matching rules (e.g. `python-fastapi.md` for backend work).
6. **Apply**: execute the workflow phases manually (DSH has no slash-command
   autoload), honoring the run-order and stop condition. Keep the user informed
   in Vietnamese.
7. **Report** with the output template below; never dump the catalog.

## Output template (match mode — keep ≤ 12 lines)

```
Workflow: <one-sentence restatement>
Best fit: <family> — <why>
Run-order: /<cmd1> → /<cmd2> → ... (from shim)
STOP when: <condition from shim grep>
Apply: <what I will do now, first concrete step>
Source: .agents/workflows/<cmd>.md
```

For autonomous loops (`loop-*`, `gan-*`, `santa-loop`): always add a
max-iteration / max-cost backstop and warn about token burn.

## Non-Goals

- Not an executor of the *catalog* — applies the matched workflow only.
- Not deep per-command docs (`ecc-guide` covers that).
- Not prompt rewriting (`prompt-optimizer`).
- Never re-enumerate `.agents/workflows/` — the table above is the live map.
