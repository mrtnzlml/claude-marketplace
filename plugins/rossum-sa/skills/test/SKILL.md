---
name: test
description: Verify that changes to a Rossum implementation preserve behavior. Captures a "before" snapshot of annotation outputs, replays the same documents against the upgraded implementation, and diffs the "after" outputs against the snapshot. Use after an upgrade, refactor, or any change intended to be behavior-preserving. Triggers on "test this upgrade", "verify this change", "regression test", "check behavioral equivalence", "did my changes break anything", "test before promoting".
argument-hint: [path-to-implementation] [--corpus=<ids-file>] [--env=<env-name>] [--canary] [--skip-static]
allowed-tools: Read, Grep, Glob, Bash, Agent
context: fork
---

# Test Rossum Implementation

You are a Rossum.ai Solution Architect verifying that a change to a customer's implementation preserves behavior. The core goal is **behavioral equivalence**: for a representative corpus of documents, the upgraded implementation should produce the same observable state as the original.

> Path or context: $ARGUMENTS

## Safety: Remote API Confirmation Gate

<HARD-GATE>
Before ANY API call or CLI command that **creates, modifies, or deletes** resources in a remote Rossum environment, you MUST:

1. **Present exactly what will be done** — tool name, target environment, what gets created/changed/deleted
2. **Wait for explicit user confirmation** — do NOT batch multiple write operations into one approval
3. **Never proceed without a clear "yes"** from the user

This applies to:
- Creating the test queue via the Rossum API
- Uploading documents to the test queue
- PATCHing annotation fields during replay
- Confirming annotations during replay
- `prd2 push` commands (scoped via `-io` to indexed files only — confirm the file list before executing)

Read-only operations are fine without confirmation: listing hooks/schemas/annotations, `rossum_get_document`, `rossum_get_annotation_content`, `data_storage_find`/`aggregate` for reads.

**Never run replay against a production queue.** The test queue and any replay annotations must live in a dedicated test queue or sandbox environment.
</HARD-GATE>

## How to Use This Skill

Five phases. Phase 0 decides what testing is needed; phases 1-4 produce the test report. Use tasks to track progress.

| Phase | Reference Skills |
|-------|-----------------|
| 0 — Scope | Change manifest from `upgrade`, `__shared/discovery-checklist.md` |
| 1 — Static Validation | `rossum-reference`, `txscript-reference` |
| 2 — Build Corpus | `rossum-reference` (annotation lifecycle), `prd-reference` |
| 3 — Replay | `txscript-reference`, `mdh-reference`, `export-pipeline-reference` |
| 4 — Diff & Report | — |

### Input state

Two Rossum environments are required: `source` (old config — the behavioral ground truth) and `target` (upgraded config — the replay target). The local repo must hold the upgraded config as files for Phase 1 static checks and migration-trace extraction. Common entry points: after the `upgrade` skill (gate on whether the upgraded files have been pushed to `target` yet), after a manual refactor (change manifest comes from `git diff` in Phase 0a instead of an `UPGRADE-*.md`), or pre-promote checks on an already-deployed upgrade.

---

## Phase 0: Scope the Test

**Goal:** Understand what changed, decide which test layers are needed, confirm the target environment, and establish the export architecture.

### 0a. Read the change manifest

If the upgrade came from the `upgrade` skill, read the `UPGRADE-*.md` file it produced — this lists exactly which hooks, formulas, and schemas changed. Otherwise, run `git diff` (or ask the user for the diff) to derive the list.

**Look for migration-traceability hints.** Deactivated hooks often retain their old `settings` with inline comments like `// C00 -> F02 on schema 9579361 (NL)` that map old calculation/transformation IDs to their formula replacements. Load these into a mapping structure — in Phase 4, diff results can be enriched with "this field was migrated from hook X's calculation Y", which dramatically speeds up triage.

### 0b. Classify each change

Decide which test layers apply:

- **Dead code removal only** → static validation is sufficient, skip replay.
- **Refactor of existing hook / hook → formula migration / deprecated hook replacement** → full pipeline: static + replay + report.
- **Hook → native business rules migration** → replay mandatory; **Phase 4 must emphasize message and automation_blocker parity as first-class diff results, not "soft-fail"**. A rule that used to fire an error but now fires nothing is a hard regression even if all field values match.
- **MDH restructure** (splitting a monolithic MDH hook into per-region/per-function hooks) → replay mandatory; verify matching results and additional_mappings outputs.
- **Extraction or OCR-adjacent logic changed** → replay mandatory; flag pre-OCR hooks as in scope.
- **Export pipeline changed** → replay must drive annotations through `confirmed` and compare export outputs (see 0d for export architecture decision).

### 0c. Classify out-of-scope changes

Some changes are deliberately non-equivalent and must be excluded from the equivalence diff. Common examples:

- **Endpoint target cutover** — a hook pointing at a production Peppol/SFTP/API endpoint in `prod` now points at a test endpoint in the upgraded env. The whole point is that it sends to a different target. Phase 3 must not try to diff the response payload.
- **Deliberate behavior improvements** — upgrades that are *supposed* to fix existing wrong behavior (e.g., correcting a rounding bug). These fall outside behavior-preservation testing.

Produce an explicit **out-of-scope changes** section in the scope statement. Items listed there are documented but not diffed in Phase 4.

### 0d. Determine the export architecture

**Ask the user how export works in this customer's implementation.** This is not always visible in Rossum configuration. Three patterns:

1. **In-Rossum hook export** (default assumption) — an export hook in the queue chain posts to the target system (Coupa, SAP, NetSuite, SFTP, etc.) on the `confirmed` event. Visible as a webhook or Request Processor hook in `queue.json`. Phase 3 diffs the serialized export payload.

2. **External-service-driven export** — an external service polls Rossum for confirmed documents, performs the export itself (SFTP upload, API call, etc.), then calls Rossum's API to transition the annotation to `exported`. This service is **invisible in the Rossum repo** — there is no hook to diff, no payload to capture. The only observable signals are: (a) did the status transition to `exported`, (b) how long did the transition take, (c) were any errors recorded on the annotation or in audit logs.

3. **Hybrid** — some queues export via hook, others via external service. Determined per queue.

Based on the answer:
- **Pattern 1** → standard replay with export-payload diff in Phase 3.
- **Pattern 2** → Phase 3 drives to `confirmed` and then **polls for status transition**. Compare status-level signals only: did `confirmed` → `exported` happen, time-to-export, error count. **Do not attempt to diff an export payload — it doesn't exist in Rossum.** Surface in the report: "Export is handled externally; this skill verified only status transition, not export content."

  **Timeout sizing.** The timeout must be at least **2× the external service's polling interval**, plus processing headroom for the export itself (SFTP upload, response handling, Rossum API call back). As a default, use `3 × polling_interval` rounded up (so a 15-minute polling service gets a 45-minute timeout). Ask the user for the polling interval explicitly — don't guess. If the customer reports long export processing times or a queue-backlog behavior on the service, bias the multiplier up to `4×` or `5×` and note the rationale in the scope statement.

  **Distinguish "still pending" from "error".** When the timeout expires without an `exported` transition, check the annotation for error messages and audit logs before declaring failure. A clean timeout (no errors recorded) means the service hasn't picked up the document yet — different signal from a transition attempt that errored out. The report should differentiate these.
- **Pattern 3** → apply the right strategy per queue.

For Pattern 2, also ask whether the external service is pointed at the test environment at all — if it only polls production queues, the test queue won't be picked up and export verification is impossible without infrastructure changes. Confirm before starting Phase 3.

### 0e. Determine the test environment

The skill needs **two coexisting states**: a `source` running the old config (for historical ground truth + optional pre-upgrade determinism check) and a `target` running the upgraded config (for replay). Three deployment shapes satisfy this:

- **Separate sandbox org with the upgrade pushed** (preferred — strongest isolation, independent credentials, no shared MDH/hooks).
- **Sibling test queue in the same org as prod** (e.g., `Netherlands_test_<date>`). Same org → same MDH datasets, possibly shared hook endpoints. Usable when no sandbox is available. Caveats to surface to the user before approving:
  - Hooks referenced by URL must be duplicated in the deploy, not re-referenced — otherwise the upgrade will replace the prod hook for prod too.
  - MDH write operations in the upgraded config would hit the prod dataset. Read-only queries are fine.
  - External export services (Pattern 2): confirm their filter. If they filter by queue ID, the test queue is invisible to them (safe). If they filter by org or status, they *will* pick up the test queue (unsafe without further gating).
  - Org-level rules are shared; per-queue attachment is the isolation layer.
- **Fresh org spun up for the test** — most isolated, highest setup cost. Reserve for major migrations.

Never run replay against the source/prod queue itself.

**If the upgrade is local-only** — `upgrade` skill produced modified files but nothing has been pushed yet — Phase 3 cannot replay against files on disk. Before Phase 3, the upgraded config must be pushed to a target via `prd2 push`. (`prd2 deploy` is not used — it requires a pre-existing deploy template.)

**Scope the push to only the upgrade's files**, not everything dirty in the working tree:

1. Start from a clean target-env subdirectory, or at minimum know what's dirty in it.
2. Stage exactly the files the upgrade modified: `git add <target-env-dir>/<files-from-upgrade-manifest>`. The `UPGRADE-*.md` produced by the `upgrade` skill lists the affected hooks/formulas/rules; derive file paths from those. If no manifest exists, use `git status <target-env-dir>` to review and stage selectively.
3. Run `prd2 push <target-env> -io` — the `-io` / `--indexed-only` flag pushes only files that are in the git index, leaving unindexed dirty files (unrelated WIP, test artifacts) untouched on the remote.
4. **Gate the push call.** Before executing, summarize the staged file list + destination for the user and wait for explicit "yes" — this is a remote write.
5. After replay + report, the user decides whether to commit the staged changes or reset them.

Autonomous queue creation (new test queue from scratch via raw API calls) is possible but involves 10+ write ops and cleanup obligations; prefer the `prd2 push` path with a sibling-queue-naming convention over ad-hoc API calls.

**Backup prerequisite?** A pre-upgrade `prd2 pull` of the source is **not** required by this skill — historical annotations come from the live source env, not from files. A pull backup is only essential if the upgrade has already been applied destructively to the only env (no source running the old config anywhere). In that scenario, behavioral replay is impossible and the skill can only do static-from-manifest review.

### 0f. Identify always-divergent formulas (auto-out-of-scope)

Some formulas embed identity-bearing references that will always differ between prod and the test environment even if the upgrade is perfect. Grep each new formula for these patterns and pre-mark them out-of-scope:

- `field.annotation_id` or any reference that interpolates the annotation URL/ID
- Hard-coded queue IDs, schema IDs, org IDs, or workspace names
- Hook-log URL embeds, training-mode flags that reference environment-specific endpoints
- Timestamp-of-now expressions (`now()`, current-date builtins) if the test runs at a different time than the prod capture

Example patterns commonly found: `sf_rossum_document_link`, `annotation_id` (when used as a formula target), `desc_start` (when seeded from URL). Add these schema_ids to the scope statement's **out-of-scope formula targets** list. Phase 4 will suppress them from hot-surface scoring.

### 0g. Scope output

Produce a scope statement listing: what changed, which layers apply, change classifications, out-of-scope changes (including the always-divergent formula list from 0f), export architecture, target environment (and confirmation that the upgraded config is deployed there, not just local), target corpus size. Create a task list with one task per applicable phase.

---

## Phase 1: Static Validation

**Goal:** Catch config-level breaks before spending API calls on replay. No API calls needed.

**For projects with more than ~5 queues, implement these checks as a single batch script over the whole `workspaces/` tree rather than running them per-queue interactively.** At scale, a per-queue walkthrough becomes intractable.

### 1a. Schema reference check

For each new formula file and each modified hook, find `field.<name>` references. A reference resolves if the name exists **as the `id` of any node in the schema tree** — including datapoint, multivalue (line_items, tax_details, etc.), tuple, and section nodes. Do not restrict to datapoints only; formulas legitimately access multivalue containers via `field.line_items.all_values` and similar patterns.

Common defects this catches:
- **Typos** — `field.ditem_ate_prepaid_start` instead of `field.item_date_prepaid_start`. Bulk migration scripts produce these in batches across many queues simultaneously.
- **Dangling references** — formulas that reference a field the upgrade removed.
- **Cross-queue schema drift** — a formula copied from a queue that defines the field to a queue that doesn't.

### 1b. Formula constraints

For each formula `.py` file:
- Under 2000 characters
- Parses as valid Python
- No `return` at the top level
- No import of HTTP libraries (formulas can't make network calls)
- No self-reference (formula must not read `field.<this_field>`)

### 1c. Hook chain integrity

For each `queue.json`:
- Every hook URL in the chain references a hook file that exists
- `run_after` references resolve to valid hook URLs
- No circular `run_after` cycles
- Deprecated hook templates (Copy & Paste, Find & Replace, Value Mapping, Date Calculation) are fully removed from the chain or marked `active: false`

### 1d. MDH references

If the `rossum-api` MCP tools are available:
- Every collection name in matching configs exists (`data_storage_list_collections`)
- Every field used in `$match`, `$sort`, or `$search` has a supporting index

### 1e. Rule references

Every field ID referenced by a rule exists in the schema. Every rule URL attached to a queue resolves to a rule file that exists.

### 1f. Hard gate on failure

**If any Error-severity check fails, Phase 1 blocks.** Do not proceed to Phase 2 until the user has fixed the defects or explicitly overridden with `--skip-static`. Building a corpus and standing up a test queue is wasted work if the implementation has broken references — the replay itself will fail in ways that mask the real defects.

**Artifact:** Static validation results, pass/fail per check, with file paths and grouped by defect pattern. Attached to the final report.

---

## Phase 2: Build Test Corpus

**Goal:** A set of annotation IDs to replay, stored outside the project tree, with "before" snapshots.

### 2a. Select annotations

If the user passed `--corpus=<file>`, use that list. Otherwise, stratify-select from the production queue's recent history:

- **N automated annotations** (status: exported, automated without user intervention) — covers the happy path
- **N manually reviewed annotations** (status: confirmed or later, with user edits) — covers edge cases
- **Per-vendor sampling** if MDH matching is in scope — one per top-10 vendors by volume
- **Force-include** any annotation that historically triggered each business rule the upgrade touches

Default N = 20 per stratum (tune via `--corpus-size`). Pull via `rossum_search_annotations` or `rossum_list_annotations`.

### 2b. Per-queue coverage rule

For projects with more than one queue in scope, **at minimum one automated annotation and one manually reviewed annotation must be selected per queue**, independent of the per-stratum counts. For projects with more than 5 queues, this per-queue floor replaces the flat N as the dominant constraint — a flat 20-per-stratum corpus cannot cover 23 regional queues. At scale, target a corpus of roughly `queues_in_scope × (5 to 15)` annotations.

Force-include edge cases specific to each queue:
- Any annotation that triggered a business rule the upgrade touched in that queue
- At least one line-item-heavy annotation (≥10 line items) per queue when line-item formulas changed
- Region/variant-specific cases — when the upgrade has region-scoped hooks or formulas (e.g., country-specific regulatory logic, currency-specific rounding), force-include an annotation per regional variant

### 2c. Capture snapshots from two sources

- **Historical capture (always).** For each selected annotation, fetch its final state via `rossum_get_annotation_content`. Record: every field value, every `validation_source`, all messages, all automation_blockers, final status, export payload if exported (or export timestamp/errors for external-export cases). This is the ground truth the upgrade is supposed to preserve.
- **Fresh capture (optional, gated).** Replay each corpus annotation through the *current* (pre-upgrade) implementation using the same mechanism as Phase 3, then diff against the historical capture. Detects non-determinism and environment drift. **Skip by default** — this step uploads documents into the source env (typically prod), which is a real write with real side-effects. Only enable when the user confirms the source env has a safe replay target (e.g., a dedicated "shadow" queue, automation disabled during the test window, or external export services filtered off).

### 2d. Store out-of-repo

Snapshots go outside the project tree. Default: `$PROJECT_ROOT/.test-runs/<timestamp>/` (add `.test-runs/` to `.gitignore`). Fall back to `~/.rossum-test-runs/<project>/<timestamp>/` if the project directory is read-only.

```
.test-runs/<timestamp>/
├── corpus.json                    # list of annotation IDs + metadata + per-queue assignment
├── migration-trace.json           # old→new mapping extracted from hook comments (Phase 0a)
├── before/
│   ├── historical/
│   │   └── <annotation_id>.json   # snapshot from existing annotation
│   └── fresh/
│       └── <annotation_id>.json   # snapshot from pre-upgrade replay
└── after/                         # populated in Phase 3
    └── <annotation_id>.json
```

**Artifact:** Corpus file + before-snapshots on disk.

---

## Phase 3: Replay

**Goal:** Produce an "after" snapshot per corpus annotation by running the same document through the upgraded implementation.

### 3a. Default mode — Confirmed-annotation replay

For each corpus annotation, run this sequence:

1. **Fetch the document.** Use `rossum_get_document` to get the source document file.
2. **Upload to the test queue.** Post the document via the Rossum upload API. Wait for OCR and `started` / `initialize` hook events. **Confirm with user before the first upload — this is a write op.**
3. **Overwrite captures.** PATCH the new annotation with the field values from the "before" snapshot. Two modes (ask user in Phase 0):
   - **Full overwrite** (default) — overwrite every captured non-formula datapoint to eliminate OCR drift.
   - **Human-edited only** — PATCH only datapoints where the prod snapshot's `validation_sources` contains `"human"`. Leaves extraction to uatv2's OCR; faster but accepts OCR drift as noise.

   **Multivalue row reconciliation (critical).** PATCH only updates values in existing datapoints — it does not change the *number* of rows in a multivalue. When prod and the test annotation have different row counts (e.g. prod extracted 0 line items, test extracted 5), you must explicitly reconcile:
   - Rows in test but not in prod → `remove` the extra tuples via the operations API.
   - Rows in prod but not in test → `add_empty_tuple` on the multivalue parent, then PATCH the new datapoints.
   - Skip reconciliation only under **human-edited-only** mode and record the row-count mismatch so Phase 4 can classify those branches as OCR drift (soft-fail, not regression).

   Use bulk PATCH (all ops in one call) by default. If `--sequenced` is passed, replay edits in the order recorded in the original audit log. This fires `user_update` events; wait for dependent hooks to settle.
4. **Confirm the annotation.** POST the confirm action. This fires `confirmed` hooks and triggers the export pipeline if configured.
5. **Verify export** using the strategy determined in Phase 0d:
   - **Pattern 1 (in-Rossum hook):** capture the export hook's output payload and any response-parsing results.
   - **Pattern 2 (external service):** poll the annotation status with a timeout (sized per Phase 0d — typically 3× the polling interval). Record: did `confirmed` → `exported` transition happen, how long it took, any error messages attached to the annotation, any relevant audit log entries, and whether a clean timeout vs. an errored transition occurred. **Do not capture a payload — there isn't one visible from Rossum.**
   - **Pattern 3 (hybrid):** apply the right strategy per queue.
6. **Capture the after-snapshot.** Same shape as the before-snapshot: field values, messages, automation_blockers, status, and the export signal appropriate to the architecture.
7. **Store** under `after/<annotation_id>.json`.

### 3b. Fallback — Hook-level payload replay

Use this when Phase 3a surfaces a diff and we need to pinpoint which hook caused it, or when the upgrade only touches a single hook and full-pipeline replay is overkill.

1. For the modified hook, fetch the last N invocations via `rossum_list_hook_logs`.
2. POST the same request payload to the upgraded hook endpoint (or invoke TxScript locally if it's a serverless function).
3. Diff the `operations` array, messages, and any state changes.

Isolates hook behavior without any of the lifecycle complexity.

### 3c. Canary mode — `--canary` flag

Opt-in mode for high-risk rollouts. Stands up a sibling queue with the upgraded config, duplicates incoming real traffic for a user-specified window (default 24h), and compares outputs continuously. Not used by default — only when the user explicitly requests shadow-mode testing.

### Side-effect policy

Before running replay, explicitly configure and **confirm with the user**:

- **MDH calls** — point to a frozen test dataset, or use the prod dataset if queries are read-only. Never mutate prod MDH collections during replay.
- **External API calls (export endpoints, notification webhooks)** — mock, point at a test endpoint, or skip with a flag. Never fire real export calls to prod target systems during replay. This applies equally to Pattern 1 (export hook) and Pattern 2 (external service pointed at the test queue).
- **Email sends** — disable in the test queue's configuration or stub.

**Artifact:** `after/` directory populated with after-snapshots.

---

## Phase 4: Diff & Report

**Goal:** Compare before vs. after, group failures by root cause, and produce the test report.

### 4a. Per-annotation diff

For each annotation, compare historical before-snapshot vs. after-snapshot:

- **Field values** — match per `(schema_id, path, row_index)` with the value-normalization spec below
- **Messages** — match by (field, content, severity). **When Axis "hook → native rules" is in scope, treat message differences as first-class diffs, not soft-fail.**
- **Automation blockers** — match by `(schema_id, type)` first, then message content. **First-class diff result** — a missing or added automation_blocker is always a hard-fail unless explicitly marked out-of-scope.
- **Export signal** — depending on Phase 0d:
  - **Pattern 1:** diff the export payload (JSON deep-diff, XML semantic diff, or byte-for-byte depending on format).
  - **Pattern 2:** compare status transition (did both reach `exported`), time-to-export (within a tolerance window), and presence of errors.
- **Final status** — exact match (confirmed, exported, rejected, etc.)
- **Automation-downgrade** — prod annotation was `automated=true` but test annotation stayed in `to_review` / has a new blocker. **First-class diff result** — hard-fail regardless of field parity, because the business outcome (auto-processing rate) changed.

**Value normalization (before comparing two field values):**
- Strip leading/trailing whitespace, including non-breaking spaces (`\u00a0`).
- If both sides parse as numeric: compare as `Decimal`; treat `"7 452.300000"`, `"7452.3"`, `"7 452,3"` (EU locale) as equal. Tolerate thousands separators in any of `[" ", "\u00a0", ",", "."]` by stripping them after detecting the decimal separator.
- Drop trailing zeros from decimal fractions (`"1.000000"` → `"1"`).
- `None`, `""`, and the string `"null"` are equivalent.
- Case-sensitive string compare otherwise.

**Diff classification ladder (apply top-down, first match wins):**

| Class | Severity | Rule |
|-------|----------|------|
| `annotation_identity` | out-of-scope | schema_id is on the Phase 0f always-divergent list |
| `structural_expected` | out-of-scope | schema_id is in the declared structural_new / structural_removed sets |
| `ocr_drift_line_items` | soft-fail | diff lives under a multivalue subtree whose prod row count was 0 and human-edited-only mode is active |
| `formula_crash` | **P0 critical** | blocker message contains `Traceback`, `Exception`, or `TypeError` |
| `automation_downgrade` | hard-fail | prod `automated=true` and test has any new blocker |
| `hot_surface_value` | hard-fail | schema_id in the "fields to pin" list from Phase 0 and values differ after normalization |
| `blocker_missing` | hard-fail | prod had a blocker of type `extension` or `error_message` that the test does not reproduce |
| `blocker_new` | hard-fail if prod was automated, else soft-fail | test has a new blocker absent in prod |
| `numeric_formatting` | soft-fail | both sides parse as numeric and are equal after `Decimal` normalization |
| `message_wording` | soft-fail | same schema_id, same blocker type, only message text differs |
| `field_value` | hard-fail | fallback for value diffs not absorbed above |

Classify each annotation's overall verdict as **pass** (no hard-fails), **soft-fail** (soft-fails only), or **hard-fail** (≥1 hard-fail or P0).

### 4b. Group failures (cross-corpus clustering)

Cluster hard-fails by `schema_id` (or `(schema_id, row_class)` for multivalue fields). For each cluster, emit:

- **Fan-out:** "N/K corpus annotations show this diff" — this is the signal that distinguishes a systemic regression from a one-off edge case.
- **Affected annotation IDs.**
- **Example values:** min 2 before/after pairs, including at least one that shows the largest absolute delta (for numeric) or the clearest string difference.
- **Likely root cause:** cross-reference the change manifest and the migration-trace mapping from Phase 0a — the F## or PM## source-ID is often available. Name the formula file or rule when you can.
- **Suggested fix.**

P0 formula crashes get their own cluster at the top of the report regardless of fan-out — a crash affecting 1/K is still a bug.

### 4c. Coverage analysis

For each modified hook/formula/rule in the change manifest, record whether at least one corpus annotation exercised it (via hook logs or formula recompute logs during replay). Uncovered changes are risks — flag them prominently.

**Severity escalation.** If an observed regression cluster strongly suggests an *uncovered* path is also broken (e.g., price/quantity look swapped on non-blanket POs, which hints blanket-PO swap logic may misfire but the corpus has no blanket-PO case), elevate that coverage gap to **P0 — untestable with current corpus, likely broken**. Recommend expanding the corpus before promoting.

### 4d. Automation parity

Compute before/after:
- Automation rate
- Per-blocker-reason counts
- Per-message counts

A shift in any of these is a signal even if no individual field failed.

### 4e. Write the report

Write `TEST-[customer-or-folder-name]-[timestamp].md`. **Location is a choice, not a default:**
- In-project (committed alongside the implementation) if the customer expects test reports in the repo.
- `$PROJECT_ROOT/.test-runs/<timestamp>/TEST-*.md` co-located with the snapshot if reports should be ignored by git.
- An external outputs folder for ad-hoc exploration.

Ask the user if the target isn't obvious from context.

Report template:

```markdown
# Test Report: [Customer/Project Name]

**Test run:** [timestamp]
**Scope:** [one sentence describing what was tested]
**Export architecture:** [Pattern 1 / Pattern 2 / Hybrid — from Phase 0d]
**Verdict:** **Pass** / **Pass-with-warnings** / **Fail**

## Summary

- Corpus size: N annotations (A automated, M manually reviewed, spread across K queues)
- Pass / soft-fail / hard-fail: X / Y / Z
- Automation rate: before A% → after B% (Δ)
- Out-of-scope changes (documented, not diffed): [list]

## Static Validation

| Check | Result | Details |
|---|---|---|

## Equivalence Results

| Annotation ID | Queue | Verdict | Field diffs | Message diffs | Blocker diffs | Export signal | Link |
|---|---|---|---|---|---|---|---|

## Grouped Failures

### P0 — Formula crashes (if any)

| Annotation | Schema ID | Message |
|---|---|---|

### Group 1: [schema_id or pattern]
- Fan-out: N/K corpus annotations
- Affected annotations: [list]
- Example diffs: [2-3 before/after pairs]
- Likely cause: [cross-ref to change manifest; include migration-trace ID if available]
- Suggested fix: [...]

(Repeat per group)

## Coverage

| Change | Exercised by corpus? | Severity if uncovered |
|---|---|---|

Uncovered changes (risk-ranked): [list, elevate to P0 any gap where observed regressions suggest the uncovered path is likely broken]

## Automation Parity

| Metric | Before | After | Delta |
|---|---|---|---|

## Manual Sign-off Items

- [ ] ...
```

**Artifact:** `TEST-*.md` report.

---

## Important

- **Never run replay against a production queue.** Always a dedicated test queue or sandbox.
- **Never modify the prod MDH dataset during replay.** Use a frozen copy or read-only queries.
- **Ask about export architecture in Phase 0.** External-service-driven export (Pattern 2) is invisible in the Rossum repo; assuming Pattern 1 when the customer uses Pattern 2 will cause Phase 3 to silently look for a payload that doesn't exist. Always confirm the pattern explicitly.
- **Local-only upgrades can't be replayed.** The test environment must run the *upgraded* config; if the upgrade still lives only in local files from the `upgrade` skill, push to test before Phase 3.
- **Don't invent diffs.** Only report failures actually detected. If a check can't run (e.g., side-effect policy not configured, external service not pointed at test queue), say so explicitly rather than silently skipping.
- **Corpus quality over quantity.** A corpus of 20 well-stratified annotations usually catches more regressions than 200 random ones. Invest effort in selection, not volume. For multi-queue projects, the per-queue floor (2b) takes precedence over per-stratum counts.
- **OCR drift is noise, not signal** for behavior-preservation testing. If the upgrade is *supposed* to change extraction, that's a different kind of test and this skill isn't the right tool.
- **At scale, script Phase 1.** Per-queue interactive checks become intractable beyond ~5 queues; prefer a batch script over `workspaces/`.
- **When unclear, confirm.** Any write op against a remote environment passes through the hard-gate.
