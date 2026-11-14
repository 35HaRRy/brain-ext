# Notion-first memory and change queue

## Intent and agreed policy

Notion is the primary workspace. Mirror Me and Carrier and their descendants for
explicit agent memory search. Brain and Agent Workspace retain their existing
operational roles. Roots are configured by immutable page IDs, never guessed by
title. Linked external pages do not enlarge the read scope.

Agents may create pages under any parent accessible to the integration, without
per-operation approval. Updates and trash operations require batch approval bound
to the exact request and remote baseline. A changed baseline invalidates approval.
Conflicts never overwrite either version. Missing local files do not imply remote
deletion. Notion content remains untrusted data, not agent instructions.

## Approaches

Considered unrestricted bidirectional editing, Notion-primary suggestions, and a
Notion-primary durable operation queue. The user chose the queue policy: automatic
creation, reviewed updates/deletions, automatic remote-to-local refresh. This
avoids maintaining two independent editable copies.

## Design

- Optional `memory_root_page_ids` replaces Brain as the pull roots when configured;
  old configuration and legacy outbox push continue working unchanged.
- Reuse the existing mirror, index, path validation, lock and HTTP client.
  Deduplicate overlapping roots by Notion ID. Do not silently migrate/delete the
  existing mirror or operational task structures.
- Add a durable JSON change journal in `.brain-ext/state/changes_state.json`.
  Operations have UUIDs, immutable payloads, baseline snapshots, request hashes,
  review-bound approval hashes and lifecycle status. CLI exposes proposal,
  listing/diff, batch approval, application and cancellation.
- Updates use one exact, unique `old_str`/`new_str` replacement, not whole-page
  replacement. Incomplete Markdown is not writable. Structural Notion tags are
  excluded from these text edits. Rich document transformations are not a v1 goal.
- Deletions snapshot the target subtree, including page content and properties;
  changed descendants or pending overlapping changes prevent application.
  Configured roots are protected. Trash only, never permanent deletion.
- A confirmed remote trash state is the remote deletion signal. The local journal
  records a UUID tombstone with origin, page ID and acknowledgement time. A
  standalone Notion deletion-list page is unnecessary: `in_trash` supplies the
  authoritative remote record, and avoids requiring all humans to use a special
  delete button. 403/404, incomplete scans and moves outside scope are not proof of
  deletion. Pending proposals or local edits make a remote deletion a conflict.
- Acknowledged tombstones remain in history; no automatic pruning in v1. Restored
  pages are pulled again and the historical deletion event remains acknowledged.
- Persist pending before any remote mutation. Interrupted writes become uncertain;
  future runs reconcile read-only, never blindly repeat. Creates use a visible
  UUID marker, following existing outbox practice.
- Dry-run performs no disk or remote mutation. Queue commands do not require
  model/LLM inference. Normal sync applies eligible queue items, pulls and indexes.
  Existing sync without a queue remains read-only on Notion.

## Limits and non-goals

No scheduler/webhook service, external dependency, media upload, arbitrary property
editing, automatic merges or direct modification of the managed vault runtime.
No live API/config changes during development. IDs and live acceptance are a
separate deployment step. Client preflight cannot provide server-side atomic CAS;
targeted edits reduce but do not eliminate the final concurrent-write window.
Journal state and mirror require backup together for reliable recovery.

## Acceptance

Test multi-root deduplication and legacy fallback; auto-create outside read scope;
immutable approval/diffs and stale baseline rejection; targeted updates; trash and
subtree checks; deletion/update conflicts; access loss versus trash; restore;
read-only uncertain recovery; corrupt state and path protection; dry-run byte
preservation; CLI sync and index integration. Full suite and lint must pass.
