# Notion Memory Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Notion-primary agent memory with automatic page creation, reviewed text
updates/trash, and durable deletion reconciliation.

**Architecture:** Extend existing pull with optional multi-root scope. Add a
durable operation journal and focused queue service, reuse existing API/IO/locks,
then expose commands and connect normal sync to eligible operations.

**Tech Stack:** Python >=3.11, existing httpx/PyYAML, pytest and ruff; no new dependencies.

**Spec:** `docs/superpowers/specs/2026-11-14-notion-memory-queue-design.md`

## Global Constraints

- Notion is primary; memory_root_page_ids is explicit and defaults to legacy Brain.
- Automatic creates at any accessible parent; update/delete require hash-bound approval.
- No live Notion mutation or real configuration modification during development.
- Incomplete reads, corrupt state and conflicts fail closed; dry-run is non-mutating.
- Trash only; protect roots; keep acknowledged UUID tombstones.
- Preserve existing legacy outbox and managed task workflows.

## Review Focus

- Nested/overlapping roots must neither duplicate nor archive each other's pages.
- Lost access/moved pages must not be interpreted as confirmed deletion.
- Remote deletion must not discard pending operations or local human edits.
- Stale subtree approval must not cascade-delete new/changed descendants.
- Interrupted writes must not create duplicates or replay stale updates.

## Task 1: Multi-root memory scope

**Files:** config.py, notion/pull.py, cli.py, tests/test_memory_scope.py.
**Interfaces:** Config.memory_root_page_ids tuple[str, ...]; pull signature unchanged.

- [x] Write tests for tuple/TOML validation, multi-root union, overlap and fallback.
- [x] Run tests and observe missing-field failures.
- [x] Implement validated optional roots and union inventory.
- [x] Verify scope tests and existing notion/core tests.

## Task 2: Durable proposal and approval journal

**Files:** notion/changes.py, tests/test_notion_changes.py.
**Interfaces:** propose(config, client, action, target, ...), review(config),
approve(config, items), cancel(config, ids), apply(config, client, ...).

- [x] Write failing tests for create/update/delete proposals, exact diffs, immutable
  hashes, explicit batch approval and invalid baselines.
- [x] Implement journal validation, snapshots and local queue operations.
- [x] Write failing tests for eligible execution, subtree trash, partial reads,
  approval invalidation, uncertain recovery, corruption and dry-run.
- [x] Implement pending-before-write, readback and read-only recovery.
- [x] Run queue tests and existing notion regression tests.

## Task 3: Deletion reconciliation and user-facing integration

**Files:** notion/pull.py, notion/changes.py, cli.py, tests/test_memory_scope.py,
tests/test_notion_changes.py, README.md, docs/NOTION_MEMORY_QUEUE.md.
**Interfaces:** pull checks journal blockers and records confirmed trash history;
CLI changes verb routes queue operations; sync applies then pulls/indexes.

- [x] Write failing tests for remote trash, access loss, pending-update conflict,
  local file loss, restoration, nested trash and CLI dispatch/dry-run.
- [x] Implement safe tombstone acknowledgement and commands; update doctor roots.
- [x] Document exact commands, approval boundary, backup and deployment requirements.
- [x] Run full pytest, ruff and git diff --check; obtain a fresh read-only review.

## Execution ledger

- Baseline: 251 passed, 4 skipped.
- Ruling: Work in the existing clean `development` branch; no worktree created
  without consent. No commit, push or live deployment is included in this request.
- Ruling: Record agreed design here and proceed under the user's explicit
  development authorization instead of requesting a second planning approval.
- Pre-flight: Task 1 pull/config feed Task 3; optional roots keep legacy signatures.
  Task 2 journal is shared by Task 3 pull and CLI; use one common operation lock,
  never nested acquisition.
- Task 1: complete — four new tests RED→GREEN; 76 focused tests passed.
- Task 2: complete — 26 queue tests RED→GREEN; 85 scope/queue/Notion tests passed.
- Task 3: integration RED→GREEN; full suite before final review: 298 passed, 4 skipped.
- Final review: two Important findings reproduced in new failing tests: legacy
  absence-as-deletion and stale search membership after move. Both fixed; 126
  focused tests passed. Confirmed-trash safety now applies to legacy roots too;
  the old archive fixture explicitly marks its deleted page in_trash.
- Ruling: A tiny per-page scope marker under `.brain-ext/scope/` revokes search
  membership after a confirmed move while preserving mirror bytes; re-entry clears
  the restriction. Cost: these markers must travel with recovery state/backups.
- Agent instruction baseline: independent reader found old instructions restricted
  creation to Agent Workspace and lacked queue/approval/deletion flow. Updated
  source skill/rules, not the installed vault copies. Fresh behavioral recheck
  correctly followed auto-create, reviewed update/trash, deletion conflicts and
  writable sync. Clarified tool-execution permission versus content approval.
- Additional safety checks: immediate create readback uses the returned page ID
  rather than failing on an unrelated partial sibling (RED→GREEN); malformed scope
  markers fail closed (RED→GREEN); human list shows IDs/hashes/diffs, and deletion
  review includes descendant titles. CLI body-file privacy is covered.
- Final verification: `python -m pytest -q --tb=short` → **307 passed, 4 skipped**
  (115.51s); `ruff check .` and `git diff --check` clean. No production code
  changed after this full run. No deferred minor review findings.
- Delivery: uncommitted changes retained in the existing development checkout;
  no merge, push, live root lookup, real config update, vault installation or
  live Notion creation/update/trash was performed.

## Live deployment follow-up — 2026-11-14

User supplied Me and Carrier URLs and authorized the next setup step.

- [x] Parse immutable roots: Me `a3c50592-dec8-410b-b6f0-acff7be786fd`;
  Carrier `e612edbd-19eb-448d-948c-d98b87678426`.
- [x] Verify both roots are accessible and active with two guarded GET requests.
- [x] Back up original config and installed skill/rules, verify known baseline
  before replacing; retain all vault-specific paths, text-search and disabled MCP.
- [x] Add only memory_root_page_ids to real config; preserve Brain/Agent Workspace.
- [x] Install source skill and common rules; update the local operational paragraph
  to use the queue policy rather than obsolete Agent Workspace-only note writes.
- [x] Offline assertions: unrelated config unchanged, installed skill byte-equal
  to source, common rules equal to source, opencode.json unchanged, MCP disabled,
  all 18 existing mirror/outbox/state files byte-preserved, queue empty.
- [x] Bounded read-only previews ended with explicit timeout status; protected
  files compared unchanged. Full preview completion was not claimed.
- [x] User-authorized real pull/index executed; partial result with eight marked
  pages, local integrity/index verified. See final import record below.
- [ ] Live write/trash acceptance: a later explicitly scoped step.

Rollback copies and verification manifest:
`C:\Users\35.HaRRy\AppData\Local\Temp\opencode\brainext-memory-deploy-ntn518lw`.
No token or note body was printed or stored in these deployment reports.

Preview restart: first uninstrumented job exceeded two hours without a result.
User explicitly approved stopping/restarting it. Its creation time and child
process ownership were verified before termination. New temporary probe records
sanitized progress every 30 seconds and uses a 600-second watchdog with explicit
timeout/partial status. Synthetic self-test passed for remote mutation guard,
deadline guard and sanitized counters. Results remain pending; no real pull/index
or Notion mutation has been performed.

User subsequently authorized the first real pull and local index with `başla`.
An instrumented import wrapper was self-tested using synthetic HTTP and SQLite:
`IMPORT_SELF_TEST_PASSED`. Initial live job started with backup-before-write,
remote read-only guard, no queue apply/push, network blocked for local index,
30-second sanitized progress, and a four-hour cooperative safety deadline.
Job directory: deployment backup folder / `initial-import-20261114`.
Completion and full-corpus verification remain pending; do not mark them complete
from job launch alone.

Final import record: 6623.3 seconds; overall partial (exit_code=2), pull
7639 new / 1 updated / 12 archived / 0 failed; 8 incomplete Markdown pages.
Local text index succeeded: 7646 documents (7640 active mirrors + 6 local),
both roots indexed, 40882 chunks/FTS rows. Offline integrity verification found
zero mirror hash conflicts; all 12 archived bodies match backup; outbox unchanged,
operation lock released, zero remote mutations. Reports in the job directory:
`import-result.json`, `offline-verification.json`, `partial-pages.json`.
The eight partial pages still block full-content acceptance; no blind rerun or
remote write/trash test has been started.

Restart result: watchdog timeout at 600 seconds; 1350 HTTP 200 responses,
1283 block-children calls, 64 data-source queries, no Markdown reads yet.
Stack shows first-root inventory traversing nested blocks below database rows.
No throttling/error retry was observed. This is ongoing expensive discovery,
not evidence of one hung request. Protected 18 files/config/instructions remain
unchanged. Preview remains incomplete; do not start real pull/index from this
result. The direct page-GET counter is not a total discovered-page count.
