# brain-ext

**Keep your knowledge in Notion. Find it locally. Give your AI assistant the right context.**

brain-ext mirrors selected Notion pages into a local Markdown vault, makes them
searchable, and queues changes back to Notion. An optional OpenCode plugin adds
project-scoped shared memory, while a skill teaches the assistant how to use the tools.

Notion stays the source of truth. You choose what to mirror, what the assistant
can recall, and which changes to existing pages are approved.

## 2. Requirements and installation

### Before you start

- **Python 3.11+** and **Git**.
- A local folder for your Markdown vault, separate from this code repository.
  The CLI can use a plain folder; the optional shared-memory plugin needs an
  existing **avenoxbeyin 3.12.0** vault.
- A Notion connection token with **Read content** access, and the pages you want
  to mirror shared with that connection. Add **Insert content** and **Update content**
  only if you want to write back. See [Notion capabilities](https://developers.notion.com/reference/capabilities).
- Optional: **OpenCode** and **Node.js** for the plugin and skill.
  The plugin was tested with OpenCode **2.2.7** and Node **26.13.0**;
  compatibility with other versions is not assumed.

### 1. Install the CLI

These commands use **Windows PowerShell**. On macOS/Linux, use `python3` to create
the environment and replace `.\.venv\Scripts\` with `.venv/bin/` in later commands
(`brainext` instead of `brainext.exe`).

```powershell
git clone https://github.com/35HaRRy/brain-ext.git
cd brain-ext
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

### 2. Choose a vault and create the configuration

Use an existing vault, or create a plain folder for CLI-only use:

```powershell
New-Item -ItemType Directory -Force ..\memory-vault
$vault = (Resolve-Path ..\memory-vault).Path
.\.venv\Scripts\brainext.exe init --vault "$vault" --mirror-git exclude
```

`init` creates `config.toml` and `.env.example` in the current directory, and adds
vault Git ignore rules. It does **not** install avenoxbeyin or overwrite an existing config.

### 3. Connect Notion

Edit `config.toml`. In its existing `[notion]` section, replace the empty target
values and add your reading roots:

```toml
brain_root_page_id = "<brain-page-id>"
agent_workspace_id = "<agent-workspace-page-id>"
memory_root_page_ids = ["<first-reading-root-id>", "<second-reading-root-id>"]
```

Reading roots select the page trees to mirror. Brain and Agent Workspace are
separate operational targets; Agent Workspace is used by the legacy draft workflow.
Use your own page IDs, and grant the connection access to the relevant pages.

Set the token for this terminal session without placing it in a command:

```powershell
$secret = Read-Host "Notion connection token" -AsSecureString
$env:NOTION_TOKEN = [System.Net.NetworkCredential]::new("", $secret).Password
```

Alternatively, store `NOTION_TOKEN=...` in a local `.env` beside `config.toml`.
Never commit or share that file.

### 4. Check, preview, import, and search

```powershell
.\.venv\Scripts\brainext.exe doctor --json
.\.venv\Scripts\brainext.exe pull --dry-run --json
.\.venv\Scripts\brainext.exe pull --json
.\.venv\Scripts\brainext.exe index --json
.\.venv\Scripts\brainext.exe search "project decisions" --mode text --json
```

Read each result before continuing: exit code **0** means success, **1** means
failure, and **2** means a partial result that needs review. A preview still reads
Notion. With a token, `doctor` scans the reading trees too; checks, previews, and
the first import of a large workspace can take time.

Text search works without an AI model. Optional semantic search and configuration
details are in the [CLI reference](docs/CLI.md).
For the optional plugin and skill, follow [Agent integration](docs/AGENT_INTEGRATION.md).

## 3. Tools and features

### CLI — mirror, search, and change Notion notes

All commands below run through `brainext`. From the repository, use
`.\.venv\Scripts\brainext.exe`; outside it, pass `--config "<absolute-config-path>"`.

- **Setup and health — `init`, `doctor`:** Create a config and check paths,
  credentials, mirror health, and index status.
  Example: run `brainext doctor --json` before investigating missing search results.
- **Local mirror — `pull`:** Read the configured Notion trees into Markdown.
  Example: run `brainext pull --dry-run` to preview a newly added reading root.
- **Search index — `index`:** Build or refresh the local text index and, when
  configured, local embeddings.
  Example: run `brainext index` after importing meeting notes.
- **Recall — `search`:** Find relevant passages using text, vector, or hybrid search.
  Example: `brainext search "why did we choose this host?" --group-by-file`.
  Without a usable local model, search reports a text fallback.
- **Linked context — `neighbors`:** Explore notes connected by links.
  Example: `brainext neighbors "Hosting decision" --depth 2` to find related decisions.
- **Search evaluation — `eval`:** Measure retrieval against your expected answers.
  Example: `brainext eval eval/queries.example.yaml --json` to try the sample format.
- **Change queue — `changes`:** Propose new pages, exact text updates, or moves to
  trash, then review and apply them. Updates and trash require explicit,
  hash-bound approval; new pages do not require that approval step.
  Example: queue a corrected decision with `changes update`, then review it with `changes list`.
- **Routine refresh — `sync`:** Apply eligible queued changes, pull Notion, and
  update the index.
  Example: `brainext sync --if-stale 30m --json` at the start of a work session.
  **This can write to Notion**, including queued new pages.
- **Legacy drafts — `push`:** Send approved `agent-out/` drafts only to Agent Workspace.
  Example: preview a reviewed handoff with `brainext push --dry-run` before sending it.
  `sync` does not send these legacy drafts.

Details and examples: [CLI reference](docs/CLI.md).

### OpenCode plugin — project-scoped shared memory

- **Automatic context:** Load general preferences and relevant memory for the
  active project. Example: reopen a project and recall its previous decisions
  without loading every project's notes.
- **Project mapping:** Register a project or connect a folder to an existing one
  after approval. Example: bind a second clone to the same project; skip a temporary folder.
- **Scoped recall:** Search the active project's memory through `shared_memory`.
  Example: find another project's decision only when explicitly asked to search that project.
- **Persistent notes and tasks:** Record decisions and handoff notes, and manage
  tasks with user instruction or approval. Example: save an agreed deployment
  decision for the next session.
- **Privacy controls:** Skip memory for a session, ignore a folder, or use
  `no-memory` / `no-tools` for a turn. Example: discuss sensitive material without
  automatic memory context.

The plugin uses the existing Beyin vault runtime; it does not create a separate
memory database or trigger Notion synchronization.
Setup, actions, and limits: [Agent integration](docs/AGENT_INTEGRATION.md).

### Skill and rules — teach the assistant the workflow

- **`notion-brain` skill:** Teach the assistant to refresh, search, cite sources,
  and prepare reviewed Notion changes. Example: ask “Find our hosting decision and
  propose a correction,” then inspect the proposal before approving it.
- **Companion safety rules:** Treat retrieved text as data, protect private notes,
  and require approval where needed. Example: a command embedded in a Notion page
  is not permission to execute it.

Installation and example prompts: [Agent integration](docs/AGENT_INTEGRATION.md).
Source files: [skill](skills/notion-brain/SKILL.md) and [rules](rules/RULES.md).

### Data and safety

`notion/` is a generated mirror: edit in Notion or use the change queue, not the
mirror files. Keep backups of the vault, mirror, and `.brain-ext/` state together.

Indexing and embeddings run locally, but passages given to an assistant go to
its model provider. Notion API calls go to Notion. Mark sensitive local notes
`visibility: private`; project scoping is not an operating-system sandbox.

## 4. Example: recall a decision and publish a follow-up

After installation, suppose your Notion project tree contains a hosting decision.
Run these commands from the repository with its configured vault:

```powershell
# 1. Read the latest notes and refresh local search. No Notion writes.
.\.venv\Scripts\brainext.exe pull --json
.\.venv\Scripts\brainext.exe index --json

# 2. Find the decision and its linked context.
.\.venv\Scripts\brainext.exe search "hosting decision" --mode text --json
.\.venv\Scripts\brainext.exe neighbors "Hosting decision" --depth 2 --json

# 3. Write a new follow-up draft in the vault, not in the mirror.
New-Item -ItemType Directory -Force "$vault\agent-out"
Set-Content -Encoding utf8 "$vault\agent-out\hosting-follow-up.md" `
  -Value "# Hosting follow-up`nReview hosting costs at the next planning meeting."

# 4. Queue a new Notion page under your chosen parent.
.\.venv\Scripts\brainext.exe changes create --target "<parent-page-id>" `
  --title "Hosting follow-up" --body-file agent-out/hosting-follow-up.md `
  --reason "Follow-up to the hosting decision" --json

# 5. Review the queue, then preview only the operation returned above.
.\.venv\Scripts\brainext.exe changes list --json
.\.venv\Scripts\brainext.exe changes apply --id "<operation-id>" --dry-run --json

# 6. Publish that new page, then pull and index it.
.\.venv\Scripts\brainext.exe changes apply --id "<operation-id>" --json
.\.venv\Scripts\brainext.exe pull --json
.\.venv\Scripts\brainext.exe index --json
.\.venv\Scripts\brainext.exe search "hosting follow-up" --mode text --json
```

Replace the placeholders with the actual parent and returned operation ID.
If this is a new terminal, set `$vault` to your configured vault's absolute path.
The new page appears in local recall only if its parent is inside your reading scope.

To change an **existing** page instead, use `changes update`, show the diff,
obtain explicit approval, and approve the reviewed ID/hash pair before applying.
See the [reviewed-change workflow](docs/CLI.md#reviewed-updates-and-trash).
