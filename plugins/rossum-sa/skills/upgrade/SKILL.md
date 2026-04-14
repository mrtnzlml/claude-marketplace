---
name: upgrade
description: Upgrade deprecated Rossum extensions to modern equivalents. Finds old Copy & Paste, Find & Replace, Value Mapping, and Date Calculation extensions and produces replacement formula fields with migration steps. Use when modernizing a customer implementation. Triggers on requests like "upgrade extensions", "migrate to formulas", "replace deprecated hooks", "modernize this setup".
argument-hint: [path-to-implementation]
allowed-tools: Read, Grep, Glob, Bash, Agent
context: fork
---

# Upgrade Rossum Implementation

You are a Rossum.ai Solution Architect upgrading a customer's implementation from deprecated extensions to modern formula fields.

> Path or context: $ARGUMENTS

## Scope

This upgrade covers **value transformations and date calculations** — extensions that copy, transform, map field values, or compute dates:

| Deprecated Extension | Replacement | Why |
|---------------------|-------------|-----|
| Copy & Paste Values | Formula field | Extension is deprecated and no longer maintained |
| Find & Replace Values | Formula field | Extension is deprecated and no longer maintained |
| Value Mapping | Formula field | Formula fields are simpler, faster, and version-controlled |
| Date Calculation | Formula field | Extension is deprecated and no longer maintained |

## Phase 1: Find Deprecated Extensions

Use the provided path (or current directory if none given). Refer to `skills/__shared/discovery-checklist.md` for glob patterns.

1. Find all hook JSON files: `**/hooks/*.json`
2. Identify deprecated extensions by **grepping hook files** for these patterns:
   - Names containing: `Copy`, `Paste`, `Find`, `Replace`, `Value Mapping`, `Mapping`, `Date Calculation`, `Date Calc`
   - Hook URLs containing: `copy-paste`, `find-replace`, `value-mapping`, `date-calculation`
3. For each match, read the **full hook JSON** — especially `settings` (the transformation rules) and `queues` (which queues use it)
4. Find the **schema** for each affected queue (`**/schema.json` in the matching queue directory) so you know what fields exist

Do NOT produce output during this phase. Read everything first.

## Phase 2: Understand Each Extension

For each deprecated extension found, extract the transformation logic from its `settings`:

### Copy & Paste Values

Settings typically contain source-to-target field mappings with optional conditions. Look for keys like `mappings`, `operations`, `source`, `target`, `conditions`. Each mapping copies a value from one schema field to another, optionally gated by a condition (e.g., "only if target is empty").

### Find & Replace Values

Settings contain regex-based find-and-replace operations. Look for keys like `operations`, `field_id`/`field`, `pattern`/`find`, `replacement`/`replace`, `flags`. Each operation applies `re.sub()` to a field value.

### Value Mapping

Settings contain value-to-value mappings. Look for keys like `mappings`, `source`, `target`, `mapping`/`values`, `default`. Each mapping translates discrete values in one field to corresponding values in another field.

### Date Calculation

Settings contain a `calculations` array. Each calculation has:
- `expression`: a string like `{date_issue} + timedelta(days=30)` where `{field_id}` references schema fields and `timedelta(days=N)` adds/subtracts time. The `timedelta` parameter can be a literal integer or a schema field reference (e.g., `timedelta(days={terms})`).
- `target_field`: the schema field ID to write the computed date to.
- `condition` (optional): a string expression that gates the calculation (e.g., `{sender_name} == 'Milk Company'`).

All fields referenced in expressions (except `timedelta` parameters) must be of type `date` in the schema. Calculations are evaluated in order — later entries can override earlier ones for the same `target_field` (useful for conditional overrides).

## Phase 3: Produce Upgrade Report

Write a markdown file named `UPGRADE-[customer-or-folder-name].md`:

```markdown
# Upgrade: [Customer/Project Name]

## Summary

One paragraph: how many deprecated extensions were found, which queues are affected, overall migration effort.

## Extensions to Upgrade

### [Extension Name] → Formula field

**Current behavior:** One sentence describing what this extension does.
**Queues:** List of queues that use this extension.

**Replacement formula:**

Create a formula field `[field_id]` in the queue schema (type: `formula`, `ui_configuration.type`: `formula`) and add the following formula file:

`formulas/[field_id].py`:
```python
# Replaces: [Extension Name]
[formula code here]
`` `

**Migration steps:**
1. Add the formula field to the schema (or change the existing field's type to `formula`)
2. Create or edit the formula `.py` file in the queue's `formulas/` directory — **never edit the `formula` property in `schema.json`** (`prd2 push` syncs the `.py` file into the JSON automatically)
3. Test that the formula produces the same results as the extension
4. Remove the extension from the queue's hook chain in `queue.json`
5. Delete the hook file if no other queues use it

(Repeat for each extension)

## Migration Checklist

- [ ] All formula fields added to schemas
- [ ] All formula `.py` files created
- [ ] All deprecated extensions removed from queue hook chains
- [ ] Tested in dev/sandbox before promoting to production
```

## Formula Field Rules

When writing replacement formulas, follow these constraints:

- **Max 2000 characters** per formula file. If the logic is too complex, split across multiple formula fields or use a serverless function instead.
- **No HTTP requests** — formulas cannot call external services.
- **No self-reference** — a formula field must never read its own value (circular reference error).
- **No return statements** — the last expression evaluated is the output.
- **Extensions cannot overwrite formula values** — if another extension needs to modify the same field, use a separate "data" type field as an intermediary.
- **Line items**: formulas on line item fields execute per-row. Use `field.<name>.all_values` to aggregate across rows.

### Replacement Patterns

**Copy & Paste → Formula:**
```python
# Simple copy
field.source_field

# Conditional copy (only if target would otherwise be empty)
field.source_field if not field.target_field else field.target_field

# Copy with transformation
field.source_field.upper()
```

**Find & Replace → Formula:**
```python
import re
# Remove non-alphanumeric characters
re.sub(r'[^A-Za-z0-9]', '', str(field.original_field))

# Normalize whitespace
re.sub(r'\s+', ' ', str(field.original_field)).strip()
```

**Value Mapping → Formula:**
```python
# Direct mapping with fallback to original value
{
    "DE": "Germany",
    "AT": "Austria",
    "CZ": "Czech Republic",
}.get(field.country_code, field.country_code)

# Mapping with default
{
    "INV": "Invoice",
    "CN": "Credit Note",
}.get(field.document_type, "Other")
```

**Date Calculation → Formula:**
```python
from datetime import datetime, timedelta

# Fixed offset: date_issue + 30 days
datetime.strptime(field.date_issue, "%Y-%m-%d") + timedelta(days=30) if field.date_issue else None

# Dynamic offset from another field (e.g., payment terms)
datetime.strptime(field.date_issue, "%Y-%m-%d") + timedelta(days=int(field.terms)) if field.date_issue and field.terms else None

# Conditional: different offset based on a field value
(
    datetime.strptime(field.date_issue, "%Y-%m-%d") + timedelta(days=14)
    if field.sender_name == "Milk Company"
    else datetime.strptime(field.date_issue, "%Y-%m-%d") + timedelta(days=30)
) if field.date_issue else None
```

## Important

- Only upgrade extensions you actually find. Do not invent issues.
- If an extension's settings are too complex for a formula (>2000 chars or requires HTTP), note it as "requires serverless function" and skip the formula generation.
- When multiple queues share the same extension, produce one formula per queue (they may need slight variations if schemas differ).
- Preserve the exact transformation logic — the formula must produce identical results to the extension it replaces.
