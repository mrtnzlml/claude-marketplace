---
name: dead-code
description: Find unused hooks, formulas, rules, labels, and engines in a Rossum implementation. Runs a deterministic detector against a local prd2 tree and produces a delete-list report. Use when pruning a customer's configuration. Triggers on "dead code", "unused extensions", "what is not used", "cleanup", "prune config", "find orphans".
argument-hint: [path-to-implementation]
allowed-tools: Read, Grep, Glob, Bash, Agent
context: fork
---

# Rossum Dead Code Analysis

> Path or context: $ARGUMENTS

## The Iron Rule

**Every finding in the report MUST come from `detect.py` output. No freestanding claims. No subagent narratives. No "I think there are about N of these."**

An earlier version of this skill let a subagent do freeform analysis and it invented "56 orphan formulas" with fabricated filenames. The script below exists to make that class of hallucination impossible. If you catch yourself writing a count that isn't in the script output, stop and re-run.

## Workflow

1. **Source selection.**
   - Local prd2 env dir (`hooks/`, `workspaces/`, optionally `rules/`, `labels/`, `engines/`) → use it. Prefer the most complete env (usually DEV / sandbox).
   - Check staleness with `git status`. If dirty or obviously old, ask the user to `prd2 pull` first.
   - No local tree → ask the user whether to pull via `mcp__plugin_rossum-sa_rossum-api__*` read-only tools into a temporary dir mirroring the prd2 layout, then run the script against that.

2. **Run the detector and show the output:**
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/dead-code/detect.py <env_dir>
   ```
   Output is markdown. Present it verbatim (or lightly framed). Don't re-paraphrase findings as aggregate prose — names are what's actionable.

3. **Spot-check at least 2 findings on disk** before presenting. Examples:
   - Orphan hook: open the JSON and confirm `queues: []`.
   - Unused label: `rg -n "<label-id>" <env>/rules/` returns 0 hits.
   - Unused engine: `rg "engines/<id>" <env>/workspaces/` returns 0 hits.

   If any spot-check contradicts the output, the script has a bug — fix it, don't edit the report.

4. **Append caveats** (see below) — the script can't see them.

5. **Report only.** The user deletes.

## What the script checks

Six high-confidence categories, all derivable from file structure:

| # | Category | Rule |
|---|---|---|
| 1 | Orphan formula `.py` | filename stem not in any schema field id of the same queue |
| 2 | Hooks with no queue attachment | `queues: []` — **except** scheduled hooks (non-empty `config.schedule.cron`), which legitimately run without a queue (cron-triggered imports, housekeeping, doctors, etc.) |
| 3 | Disabled hooks | `active: false` |
| 4 | Dead rules | `enabled: false` OR `queues: []` |
| 5 | Unused labels | no enabled rule action payload references the label id/url |
| 6 | Unused engines | no `queue.json.engine` URL points at this engine |

## What the script deliberately does NOT check

These are noisy and need human judgement. If the user asks about them, use ripgrep instead of adding script complexity:

- **Schema fields with no readers.** Many are touched via `getattr(field, …)` or consumed by Rossum internals invisibly. `rg "field\.<id>\b" <env>` to investigate specific fields.
- **Engine fields not in any schema's `rir_field_names`.** Usually a long list with low actionability — delete the engine itself (check #6) and the fields go with it.
- **Function hook drift** (`.py` ≠ `config.code`). Rare and better caught by `prd2 push` / `prd2 pull` diff.
- **Broken rule trigger field refs**, **duplicate rules**. Uncommon; spot with `rg` if suspected.

## Caveats the script cannot see (include these in every report)

- **Single-environment blind spot.** A hook may look orphan in DEV but live in PROD. Offer to rerun against other envs.
- **External triggers.** Webhook hooks invoked manually or by outside systems (SAP, B2B Router, other schedulers) look orphan. Never mark a manually-invokable hook for deletion without confirming.
- **Rossum-internal reads.** Some hidden fields are consumed by the UI or extraction engine without a `field.X` syntax — err on the side of investigating, not deleting.

## Red flags — STOP if you catch yourself:

- Writing a count you can't point to in the script output.
- Naming a hook/rule/label/engine that didn't appear in the output.
- Using vague quantifiers: "about N", "roughly", "approximately".
- Summarising findings without the names ("16 labels unused" is useless; "label `AP - CG Review` (id=4886) → delete" is actionable).
- Dispatching a subagent to "analyze the project" — run the script.

## Updating the script

If a customer's layout deviates or you want a new high-confidence check, extend `detect.py` — do not hand-patch reports to compensate. The script is the contract. Keep it minimal: new checks must be cheaply derivable from file structure and produce few false positives, otherwise leave them to manual ripgrep.
