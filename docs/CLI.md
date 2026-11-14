# CLI reference

brain-ext keeps selected Notion trees in a local Markdown vault and provides
local search and a reviewed write-back queue.
Start with the [installation guide](../README.md#2-requirements-and-installation).

Examples use `brainext` as shorthand for your installed executable. In PowerShell,
that is `.\.venv\Scripts\brainext.exe` from the repository.
Use an absolute executable path and `--config "<absolute-config-path>"` in agents,
schedulers, or other directories.

## Common options and results

Every command accepts `--config` (default: `config.toml`), `--json`, and `--verbose`.
Use `brainext <command> --help` for its arguments.

- Exit **0**: success.
- Exit **1**: failure; investigate before continuing.
- Exit **2**: partial result; inspect errors and warnings.
- `--dry-run` is available for `init`, `pull`, `push`, `index`, `sync`, and `changes`.
  It does not write local or remote changes, but commands may still read Notion.

Some CLI messages are currently Turkish, even though this guide is English.

## Configuration and setup

`init --vault "<absolute-existing-folder>" --mirror-git exclude` creates the config,
a token example, and vault ignore rules. Use `include` only if you deliberately
want the Notion mirror in vault Git history. Initialization does not install
avenoxbeyin and refuses to overwrite an existing config.

The generated config has three sections:

- `[vault]`: absolute `path` and separate `mirror_dir`, `outbox_dir`, `state_dir`.
- `[notion]`: API settings, operational page IDs, token environment-variable name,
  and optional `memory_root_page_ids`.
- `[index]`: model and search settings.

Add `memory_root_page_ids = ["<root-page-id>"]` under `[notion]` to choose reading
trees. If omitted, the legacy `brain_root_page_id` is the reading root.
Links to outside pages do not add those pages to the reading scope.
Changing roots replaces the scope rather than adding to it; back up before migration.

The token is read from `NOTION_TOKEN`, or from `.env` beside the selected config.
The token environment-variable name can be changed with `token_env_var`.
Do not put secrets in `config.toml`, source control, prompts, or logs.

`doctor --json` checks local configuration, mirror integrity, and index health.
With a token, it also scans the reading trees and checks Agent Workspace access.
This can be expensive on a large workspace; it is not just a token ping.
Without a token, remote health is not verified.

## Pull: read Notion into Markdown

```text
brainext pull --dry-run --json
brainext pull --json
brainext pull --page <page-id> --json
brainext pull --full --json
```

`pull` reads remote content and writes local mirror/state files; it never requests
remote page changes. `--page` targets a page within the configured scope.
`--full` bypasses the discovery cache, not scope or safety checks.

Discovery follows physical child pages and databases, pages through database rows,
and verified parent chains. Complete v2 Markdown speeds discovery; incomplete
content falls back to block reads. Unchanged child references are cached against
the remote revision and verified local file hash.

The initial import still reads every note and can take a long time. A dry-run
also performs discovery; it is not a cheap page count.

Missing/unsupported content is marked and reported as partial, not silently
declared complete. Disappearance or a 403/404 alone is not proof of deletion.
Confirmed trash can archive a local mirror under `_arsiv/`; local edits or pending
proposals can instead cause a conflict. Archived and out-of-scope notes leave active search.

Do not edit generated `notion/` files. The destructive local overwrite override
requires **both** `--force --confirm-force`; an agent must obtain separate approval
before using it. `--lock-mirror` makes mirror files read-only at the filesystem level.

## Index and search

```text
brainext index --dry-run --json
brainext index --json
brainext search "hosting decision" --mode text --k 5 --json
brainext search "deployment" --path-prefix notion/ --group-by-file --json
brainext neighbors "Hosting decision" --depth 2 --json
```

`index` incrementally indexes eligible local Markdown. `search` returns passages
with source information; cite the file path and Notion URL when available.
`neighbors` explores the link graph by path or title.
`--include-drafts` includes eligible drafts that are normally excluded.
Private/generated content is excluded by source eligibility rules.

### Optional semantic search

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[semantic]"
```

Installing this extra does not download a model. Obtain a supported FastEmbed
ONNX model separately, with explicit download approval, and set `model_path` in
the config's `[index]` section to its local directory. Keep `embedding_model`
consistent with those files; the generated default is
`sentence-transformers/paraphrase-multilingual-mpnet-base-v2`.

`search --mode vector` uses embeddings; `--mode hybrid` combines text and vector
ranking. Without a usable runtime/model, results report text fallback.
Do not present fallback results as semantic retrieval.

Run `index --reembed` after changing the model or embedding dimensions. It also
rebuilds derived text records when no model is configured.
No automatic model-download command is provided.

### Evaluate recall

```text
brainext eval eval/queries.example.yaml --json
```

The [sample query file](../eval/queries.example.yaml) shows the expected format.
Create your own query/expected-answer set to measure recall@5 and MRR for your vault.
Check fallback counts before interpreting a result as a semantic-search evaluation.

## Change queue

Proposals live in local state. `create`, `update`, and `delete` prepare proposals;
`apply` performs eligible remote writes. `list`, `approve`, and `cancel` work
without a Notion token; the other verbs need one.

### New pages

Write the body to an eligible Markdown file **inside the vault**:

```text
brainext changes create --target <parent-id> --title "Decision summary" --body-file agent-out/summary.md --reason "Meeting follow-up" --json
brainext changes list --json
brainext changes apply --id <operation-id> --dry-run --json
brainext changes apply --id <operation-id> --json
```

`--body-file` is vault-relative, not relative to the terminal directory.
Frontmatter is not sent as body content. Private, generated, hidden, unsafe, and
out-of-vault sources are rejected.

The parent may be an explicitly identified accessible page, database, or data source.
New pages do not need `changes approve`: `apply` or `sync` can publish them.
Creating outside the reading scope does not expand that scope.
A visible `brainext-push-id` marker supports recovery; do not remove it casually.

### Reviewed updates and trash

```text
brainext changes update --target <page-id> --old-text "One unique old sentence." --new-text "The corrected sentence." --reason "Correct the decision" --json
brainext changes delete --target <other-page-id> --reason "Obsolete duplicate" --json
brainext changes list --json
```

Show the user the targets, reasons, diffs, affected descendants, IDs, and
`request_hash` values. **Only after explicit approval of those operations:**

```text
brainext changes approve --item <operation-id>=<request_hash> --json
brainext changes apply --id <operation-id> --dry-run --json
brainext changes apply --id <operation-id> --json
```

Repeat `--item` to approve a reviewed batch; repeat `--id` to select operations.
Without `--id`, `apply` considers all eligible queued operations.
Approval is bound to reviewed content and remote revisions; changed inputs invalidate it.

Updates replace one exact, unique text span. They do not rename pages, change
database properties, rewrite whole documents, or modify structural Notion tags.
Incomplete Markdown cannot be overwritten through this workflow.

`delete` moves the target to Notion trash, potentially including descendants;
it does not permanently delete. Configured roots and their ancestors are protected.
Avoid editing the same subtree while an approved deletion is being applied.
The remote preflight and write are not an atomic compare-and-swap.

### Cancel and recover

```text
brainext changes cancel --id <operation-id> --json
```

For `conflict`, preserve versions, cancel the old proposal, and prepare a fresh
proposal from the latest remote content. Multiple proposals from the same page
revision may conflict after the first is applied.

For `pending` or `uncertain`, investigate and reconcile the remote outcome first.
Do not cancel and resend under a new ID: a timed-out write may have succeeded.
Do not edit the journal by hand.

Back up mirrors and the entire `.brain-ext/` directory together, including
`state/changes_state.json` and scope records. State contains sensitive proposed
content and recovery evidence; vault Git history alone may not include it.

## Sync: apply, pull, index

```text
brainext sync --if-stale 30m --json
```

Order: eligible queued writes → pull → index. A fresh timestamp does not bypass
active queued work. Unapproved updates/trash stay queued; eligible new pages can
be published without a separate approval verb.

**For a strictly remote-read-only refresh, use `pull` followed by `index`.**
No scheduler or webhook is installed automatically.

## Legacy push: approved Agent Workspace drafts

This older route is separate from `changes` and is not processed by `sync`.
Create a Markdown file in `agent-out/` with frontmatter such as:

```yaml
---
title: Meeting handoff
status: draft
notion_target: agent-workspace
---
Follow-up notes go here.
```

After explicit content approval, change `status` to `approved`, preview with
`brainext push --dry-run`, and obtain sending approval before `brainext push`.
Unapproved drafts are skipped; this route is restricted to Agent Workspace.

## Development checks

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check .
node --test integrations/opencode/shared-memory/index.test.mjs
```

Real-model/runtime-dependent tests may skip when their prerequisites are missing.
Historical deployment records are separate from generic onboarding:
[status](STATUS.md), [Notion queue notes (Turkish)](NOTION_MEMORY_QUEUE.md).
