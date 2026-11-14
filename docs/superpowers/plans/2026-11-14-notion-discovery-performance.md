# Notion discovery performance fix

User approved optimizing discovery without narrowing Me/Carrier scope.

## Evidence and approach

Previous 600-second probe: 1350 HTTP 200 responses, 1283 block-children calls,
64 data-source queries, zero Markdown reads. Stack was inside nested content
traversal during first-root inventory, not an error/retry loop.

Use documented complete v2 Markdown physical `<page>`/`<database>` tags for
memory-root discovery. Keep full database pagination and ancestry verification.
On incomplete, warning, unknown, folder or malformed markup use original strict
block discovery. Strict remains default for deletion preflight and legacy flows.
Reuse fetched Markdown for pull; persist child-reference cache only on real pull
and reuse only for equal remote revision plus hash-verified local owned mirror.
`--full` refreshes discovery, and dry-run remains byte-preserving.

## Checklist

- [x] Tests first: missing fast inventory option and redundant block reads failed.
- [x] Implement parser, discovery/cache/reuse, state validation and doctor wiring.
- [x] Update synthetic explicit-scope fixtures to model actual physical child tags.
  Incomplete-scan cases explicitly invalidate revision and fail both fast/fallback
  representations, rather than failing an endpoint the fast path never needs.
- [x] 72 focused tests passed; synthetic content-only containers: 102 → 2 requests,
  identical discovered pages. Deep nested child ancestry is still verified.
- [x] Full suite, lint and independent focused safety review.
- [x] Repeat bounded read-only live preview with request/page/query-row counters.
  Timeout was reported honestly; remaining fallback cause was then isolated
  with bounded samples and verified before the user-authorized real import.

## Limits and scope

No dependencies, scope cuts, Notion mutations, scheduler changes or mirror writes
during live preview. Existing uncommitted queue/deployment work is preserved.
An initial full read still needs at least one content request per new page;
the optimization removes redundant traversal, not the API's rate limit.
No commit/merge/push requested.

Verification so far: full suite **324 passed, 4 skipped** (93.17s); ruff and
diff-check clean. Focused independent review still pending. New probe self-test
also verifies database query rows contribute to the discovered-page counter,
so that counter is no longer limited to direct page GET responses. Original
live measurements preserved in `before-optimization/` under the deployment
backup directory; no note bodies or tokens are included.

Final review found unterminated folder/unknown markup could evade parser
callbacks and hide children. Reproduced with two failing cases, fixed with an
explicit structural-marker guard; four malformed-tag cases and all 21 discovery
tests pass. Final full suite **328 passed, 4 skipped** (101.29s); ruff/diff-check
clean. No deferred review findings.

New live preview started with the same 600-second cap. One diagnostic progress
sample at 120s: 6358 database rows received, 6360 distinct pages seen across
query/page responses, 38 Markdown responses completed (previous probe: zero).
Still partial and no final success claim. Even one content request per 6358
new rows needs roughly 42 minutes at the configured 2.5 requests/s, before
fallback and other discovery work. The 10-minute probe is a measurement limit,
not a claim that this initial corpus can be fully read inside that limit.

Final long probe still timed out: 219 Markdown responses, 1073 block-child calls.
Bounded technical sampling found real `<unknown>` markers despite empty
`unknown_block_ids`, no truncation and no warnings. The blocks were owned,
active, childless `link_to_page` references (both page and database targets).
Extend the existing verified-leaf link fallback rather than treating whole pages
as unsupported. Malformed/foreign/non-leaf/invalid target blocks still fall back.
Target content is never fetched. The shared Markdown converter also preserves
these references instead of producing incomplete-block placeholders.

Verification: new page/database and URL-fragment cases RED→GREEN; negative
ownership/type/children/trash cases pass. Full suite **338 passed, 4 skipped**
(86.56s), ruff/diff-check clean. Live bounded 3-row sample: all fast-path accepted,
no remaining unknown markers, 5 requests for the three rows, zero block-child
calls, zero inventory errors; protected files unchanged, no remote mutations.
Report: `discovery-leaf-link-verification.json` in the deployment backup folder.
Full-corpus acceptance and real pull/index remain unperformed. Do not present
the 3-row sample as proof all 6358+ records are fully readable.

Subsequent authorized real import: first full discovery/content read reached
7640 active mirrors with 12154 successful HTTP requests and only 52 block-child
calls; local text index completed. Overall partial due to eight explicitly marked
incomplete Markdown pages (not a performance timeout). Offline verification:
7652 mirror entries including 12 preserved archives, no hash conflicts, 7646
indexed documents, both configured roots present, zero remote mutations.
Full content acceptance still excludes the eight partial pages; details in
`initial-import-20261114/partial-pages.json` under the deployment backup directory.
