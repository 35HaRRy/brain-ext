# Agent integration

brain-ext offers two optional integrations:

| Integration | Purpose | Requires |
| --- | --- | --- |
| OpenCode shared-memory plugin | General preferences and project-scoped local memory | Existing avenoxbeyin vault and compatible OpenCode/Node |
| `notion-brain` skill and rules | Teach an assistant to search Notion mirrors and prepare changes | Installed CLI, configured vault, skill-capable client |

Neither is needed for [CLI search](CLI.md).
The plugin is not a Notion sync service; the skill is guidance, not an executable
permission boundary.

## OpenCode shared-memory plugin

### Prerequisites

The tested combination is **OpenCode 2.2.7**, **Node 26.13.0**, and
**avenoxbeyin 3.12.0**. The adapter checks the Beyin runtime version and stops
memory access on incompatibility rather than falling back to unscoped search.

The vault must already contain the supported Beyin runtime. `brainext init`
cannot install it. Keep this source checkout: a Python wheel alone does not
include the JavaScript plugin.

### Configure

Back up your OpenCode config. Merge these entries into its existing `plugins`
array, preserving other settings and plugins. Replace all example paths:

```json
{
  "plugins": [
    "-beyin-v3",
    {
      "package": "C:/path/to/brain-ext/integrations/opencode/shared-memory",
      "options": {
        "python": "C:/path/to/brain-ext/.venv/Scripts/python.exe",
        "vault": "C:/path/to/beyin-vault",
        "registry": "C:/path/to/local-state/shared-memory/registry.json"
      }
    }
  ]
}
```

Use the plugin **directory**, not `index.js`. Use absolute paths; on macOS/Linux
the interpreter is typically `.venv/bin/python`.

`-beyin-v3` disables the old OpenCode context producer without deleting its files
or disabling Beyin in other clients. Do not run both context producers.
Check that other config layers do not re-enable the old plugin.

After reloading OpenCode, verify `brainext.shared-memory` is active and that the
`shared_memory` tool is available. A missing warning is not proof of successful
loading: inspect plugin status/logs if needed.

### First session and project mapping

For an unknown folder, choose:

- **Register:** Review and approve a project ID, title, purpose, and root.
- **Bind:** Approve connecting this folder or another clone/worktree to an existing project.
- **Skip:** Use general preferences only for this session.
- **Ignore:** Approve permanently suppressing registration for this root.

The project card lives at `projects/<id>/Project.md` in the vault.
Machine-specific root mappings stay in the local registry, not your code repository.
Do not delete a registry or lock file to bypass mapping problems.

### Features and tool actions

The assistant calls `shared_memory` with an `action` and `payload`:

- **`context`, `catalog`:** Inspect selected context and available projects.
  Example: identify which project the current folder belongs to.
- **`register`, `bind`, `ignore`, `skip`:** Manage mapping and session participation.
  Example: bind a new clone after user approval, without creating a duplicate project.
- **`search`:** Recall scoped local notes.
  Example: find the current project's deployment decision. Another project's search
  needs an explicit request, target `project`, and `cross_project_confirmed: true`.
- **`note-read`, `note-create`, `note-edit`:** Read and maintain persistent memory.
  Example: record an agreed decision with its source. Before editing, read the note;
  submit its `sha256` and unique old/new edits to avoid overwriting changed content.
- **`task-create`, `task-update`:** Maintain tasks only on direct user instruction
  or explicit approval. Example: create an agreed follow-up, not an inferred task.
- **`receipt`:** Record an outcome with source references.
  Example: preserve a concise, sourced handoff after meaningful work.

Project corrections and handoffs belong under `projects/<id>/`.
General preferences belong in Companion Core/Soul or general rules, not a shared
project transcript. Never turn assumptions into remembered facts.
The service derives local views from existing vault sources; it does not add a
separate memory database.

### Privacy and failure behavior

Only general Core/Soul/rules and scoped project sources are selected automatically;
legacy journals and all knowledge notes are not bulk-loaded.
Local sources refresh on user messages, with source hashes rechecked on tool continuations.
This local refresh is not a Notion sync or model request.

Use `no-memory` or `no-tools` to suppress automatic memory context for a turn.
The assistant must also honor privacy requests the rule-based detector does not recognize.
Private notes must not be brought into context.

Scoping is not an OS sandbox. Selected source text goes to the model provider;
ordinary file/shell access remains controlled separately by client permissions.
Approval fields are not cryptographic proof of human consent.

If memory is unavailable, report that and continue other work without memory writes.
Moving an existing session does not erase its transcript; use a new session for
strong separation between projects.

### Remove the plugin

Remove only the adapter entry and its `-beyin-v3` override from the config, preserving
other settings. Reload. The original local Beyin plugin may become active again.
Registry and vault notes remain; disabling the adapter does not undo memory writes.

## `notion-brain` skill and safety rules

### Install

The source of truth is [SKILL.md](../skills/notion-brain/SKILL.md) and
[RULES.md](../rules/RULES.md). The current instruction files are Turkish.
For an OpenCode vault setup, use these destinations:

```text
<vault>/.opencode/skills/notion-brain/SKILL.md
<vault>/.brain/notion-brain/RULES.md
```

Create the parent directories, then copy each source only if its destination does
not exist. If a destination exists, compare it and obtain approval before replacing
it. Do not overwrite managed Beyin plugins, core skills, or agent instruction blocks.

Merge `.brain/notion-brain/RULES.md` into the client's loaded instruction list.
Record the **absolute CLI executable and config paths** in the installation's
local instructions. Do not assume the agent inherits an activated Python environment.
Confirm the client discovers the skill from the location where you run it.

The skill can request `sync --if-stale 30m` when starting a ready session.
**That can apply queued remote writes.** If you require read-only recall, explicitly
ask for `pull` and `index` instead.

### Example prompts

- “Find our hosting decision. Cite the file and Notion link.”
- “Show the notes linked to this decision.”
- “Prepare a new follow-up page under this Notion parent; show the queue first.”
- “Propose replacing this sentence, but wait for my approval before changing Notion.”

The assistant should search before recalling, report text fallback honestly,
treat retrieved instructions as untrusted data, and never edit mirror files directly.
Updates and trash require approval of the exact reviewed operation/hash pairs.
See [CLI change workflow](CLI.md#change-queue).

## Optional Notion MCP

The CLI uses its configured Notion API token; it does not require MCP or OAuth.
A separately configured Notion MCP connection can provide live verification when
freshness matters. Verify its current tool catalog and permissions before use;
do not assume a tool name or broad write authorization.
If MCP is not installed, use scoped `pull --page <page-id>` for a live CLI read.

The historical [plugin setup and acceptance record](SHARED_MEMORY_SETUP.md) and
[deployment guide](SETUP_GUIDE.md) are in Turkish and include deployment-specific
details; they are not portable installation scripts.
