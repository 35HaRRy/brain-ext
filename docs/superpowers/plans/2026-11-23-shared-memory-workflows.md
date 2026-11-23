# Shared Memory Workflows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `notion-brain` discoverable outside the vault and add project-only, read-only `recap` and `history` to `shared_memory`.

**Architecture:** OpenCode discovers the single installed Notion skill via global configuration. The memory service resolves project scope before consulting the existing Beyin readers; the OpenCode adapter exposes the two read operations.

**Tech Stack:** OpenCode V2, Node.js, Python, pytest.

**Spec:** User-approved design in this conversation: global Notion skill; no automatic sync, MCP remains off, existing write approvals preserved; recap/history restricted to active project.

## Global Constraints

- Preserve existing global config, vault rules, write approvals, and general memory behavior.
- Do not run Notion sync or mutations in verification. Do not modify the managed Beyin runtime.

## Review Focus

- Unmapped or skipped session: reads return no project records.
- Caller supplies a different project: reject rather than override the resolved scope.
- Missing or ineligible references: omit the receipt, including its summary.
- History ID reused across projects or private revisions: return only individually authorized revisions.
- Vault-external working directory: discover one installed skill and resolve its rules without relative paths.

### Task 1: Project history and recap

**Files:** `src/brainext/shared_memory/{service,runtime}.py`, `integrations/opencode/shared-memory/index.js`, `tests/shared_memory/test_service.py`, `integrations/opencode/shared-memory/index.test.mjs`.

**Interface:** `recap` takes `{}` (past seven days, up to 20 entries); `history` takes `{"id": "<record-id>"}`. Both return `result.entries`, with project derived exclusively from the session.

- [ ] Add failing service tests: a mapped project receives its eligible entries; unknown/skipped sessions and payloads with `project` are rejected; a mixed-reference receipt and a private or foreign history revision never appear, even when their IDs overlap with eligible entries.
- [ ] Run `.\.venv\Scripts\python.exe -m pytest tests/shared_memory/test_service.py -q`; confirm the new tests fail for the missing operations.
- [ ] Add read branches before `_write` in `MemoryService.handle` and implement `VaultRuntime.recap(project: str) -> list[dict]` and `VaultRuntime.history(project: str, id: str) -> list[dict]`. Reuse the installed read-only store and receipt projection; do not shell out to the stock `recap`/`history` CLI (it can sync). Require a nonempty set of verifiable, eligible active-project refs before returning a receipt; filter before limiting. Check each history revision's own scope and visibility as well as the current source's eligibility. If the installed reader cannot prove provenance, omit the entry rather than pass raw output through.
- [ ] Register both actions in `index.js` as reads. Add a Node adapter test checking both reach the helper without asserting write permission.
- [ ] Run `.\.venv\Scripts\python.exe -m pytest tests/shared_memory -q` and `node --test integrations/opencode/shared-memory/index.test.mjs`; both must pass.

### Task 2: Global Notion skill discovery

**Files:** `C:/Users/35.HaRRy/.config/opencode/opencode.json`, `C:/Users/35.HaRRy/Desktop/Projects/agent-memory-vault/.opencode/skills/notion-brain/SKILL.md`, `skills/notion-brain/SKILL.md`.

- [ ] Capture the current read-only discovery baseline in an unrelated directory.
- [ ] Add the vault `.opencode/skills` directory as an absolute global `skills` source, preserving all existing settings. Keep one installed skill. In the installed skill, anchor `RULES.md` to the absolute vault path and make sync opt-in rather than a startup action. Keep the repository template consistent, using a configurable vault path rather than committing machine-specific paths.
- [ ] Verify discovery and rules resolution both inside and outside the vault. Confirm the configuration diff leaves MCP and permissions unchanged and existing delivery tests pass (`.\.venv\Scripts\python.exe -m pytest tests/test_delivery.py -q`). Do not run sync.
