---
name: evaluate-namings
description: Use when evaluating or auditing naming conventions of Rossum workspaces, queues, hooks, schema fields, and MDH datasets in a prd project
---

# Evaluate Namings

## Overview

Audit naming conventions for a Rossum prd project. Profile the project first to establish context, then evaluate workspaces, queues, hooks, schema fields, and MDH datasets against their rules.

---

## Step 1: Profile the Project

Read `prd_config.yaml`. Derive and output:

| Dimension | How to determine |
|-----------|-----------------|
| **Size** | Count active use cases: small (1–2 workspaces, <5 queues/workspace), medium (3–4 workspaces), large (5+ workspaces) |
| **Deployment type** | Multiple distinct `api_base` values → **multiple organisations**; single `api_base` → **single organisation** |
| **Environments** | Subdirectory names under each directory in `prd_config.yaml` — this is the ground truth |
| **Use cases** | Union of active workspaces across all orgs (deduplicated). Exclude workspaces whose names contain: `training`, `train`, `archive`, `archival`. Not all use cases need to be in all orgs. |

**Output the profile before continuing.**

---

## Step 2: Workspaces

Format: `({abbreviation}) {workspace name} {environment}`

- All parts optional; **order is fixed**
- Abbreviation in `()`, always first
- Environment always last; **only present for single-org deployments**
- Environment bracket style flexible: `DEV`, `(DEV)`, `[DEV]`

| Issue | Bad | Good |
|-------|-----|------|
| Environment not last | `DEV Invoices (Italy)` | `Invoices IT (DEV)` |
| Abbreviation not in parentheses | `IT Invoices (DEV)` | `(IT) Invoices (DEV)` |
| Environment present in multi-org | `Acosta [PROD]` | `Acosta` |

---

## Step 3: Queues

Format: `{number} ({use case}) {queue name}`

- All parts optional; **order is fixed**
- Number prefix optional, may be followed by `.` `_` or similar separator
- Use case in `()` — mandatory when multiple sub-use-cases share a workspace
- **No environment tags** — environment belongs at workspace level
- Queue name: concise; use abbreviations, not verbose descriptions

| Issue | Bad | Good |
|-------|-----|------|
| Environment tag in queue name | `PO-backed invoices (TEST)` | `PO-backed` |
| Verbose description | `Inbox for Invoices Germany` | `(DE) Inbox` |

---

## Step 4: Hooks

Format: `({use case}) {sub use case} {name} ({extension}) [{environment}]`

- Use case in `()` — mandatory when multiple use cases exist
- Sub use case (e.g. `IN`, `OUT1`, `OUT2`) — mandatory when 10+ extensions per use case
- Extension name in `()` after hook name — mandatory when 30+ extensions total; e.g. `(MDH)`, `(REST API)`
- Environment in `[]` — preferred for single-org deployments; **tolerated in multi-org** (provides useful context about which environment a hook targets)

| Issue | Bad | Good |
|-------|-----|------|
| Missing use case (multiple exist) | `Validation #1` | `(AP) Validation #1` |
| Missing extension (30+ hooks) | `Supplier Matching` | `Supplier Matching (MDH)` |
| Extension in wrong brackets | `Validation Datasets [MDH]` | `Validation Datasets (MDH)` |
| Inconsistent sub use case ordering | `Validation OUT1` | `OUT1 Validation` |

### Dependency Chain Validation for Numbered Sub-Use-Cases

When hooks use a numbered sub-use-case prefix (`IN`, `OUT0`, `OUT1`, `OUT2`, etc.), they imply a processing chain. Validate the chain is correctly wired in the hook JSON:

1. For each hook with a numbered sub-use-case prefix, read its `.json` file
2. Check the `run_after` field — it should reference the ID of the preceding step in the chain
3. The chain must be sequential: `OUT1.run_after = OUT0.id`, `OUT2.run_after = OUT1.id`, etc.

```
# Example: correct chain
OUT0 Render Export [id: 1155497]  — no run_after (first in chain)
OUT1 CSV Payload   [id: 1155492]  — run_after: 1155497  ✓
OUT2 External Push [id: 1038769]  — run_after: 1155492  ✓

# Example: broken chain
OUT0 Render Export [id: 1155497]  — no run_after
OUT1 CSV Payload   [id: 1155492]  — run_after: 1155497  ✓
OUT1 JSON Payload  [id: 1155486]  — no run_after  ✗  fires independently
```

Flag any numbered hook that is missing `run_after` when a predecessor with a lower number exists for the same use case, or whose `run_after` skips a step.

Also flag hooks that are **disabled** (`active: false`) but not removed — these are dead code and should be deleted or explicitly documented.

---

## Step 5: Schema Fields

### General Rules
- Names as short as possible
- Line item fields: `item_` prefix (mandatory)
- Extra line item tables (not the default `line_items`): any consistent prefix per table

### Suffix Rules

| Suffix | When to use | Example |
|--------|-------------|---------|
| `_match` | MDH primary match target | `sender_match`, `item_order_id_match` |
| `{match}_{field}` | MDH additional_mapping output | `sender_match_name`, `item_order_id_match_status` |
| `_calculated` | Intermediate formula result needed downstream | `item_order_id_calculated` |
| `_normalized` | Formula doing **only** sanitization (removing extra chars, trimming, shortening) — if the formula does more, use `_calculated` | `item_upc_normalized` |
| `_override` | Manual user override | `sender_name_override` |
| `_dist` | Result of distributive webhook | `item_upc_dist` |
| `_export` | Final field before export — both `field_export` suffix and `export_field` prefix are acceptable | `item_order_id_export`, `export_filename` |

### MDH Match Field Cross-Validation

Read every MDH hook JSON (hooks whose name contains `(MDH)` or description mentions "master records"). For each `settings.configurations[]` entry:

1. `mapping.target_schema_id` → **must end with `_match`**
2. `additional_mappings[].target_schema_id` → **must start with `{primary_match_id}_`** (i.e. the primary field id as prefix, then the field-specific name)

Flag any field ID that violates these rules, noting which hook and configuration block it came from.

### Standard Field Names

Use Rossum unified names for standard extracted fields. See https://elis.rossum.ai/api/docs/#extracted-field-types for the full list.

| Field type | Correct | Bad examples |
|------------|---------|--------------|
| Document ID | `document_id` | `invoice_number`, `invoice_id`, `order_identification` |
| Header PO number | `order_id` | `po_number`, `po_id`, `order_number` |
| Line PO number | `item_order_id` | `order_id_header`, `po_number`, `order_id_line`, `order_id_export` |
| Line PO (calculation) | `item_order_id_calculated` | `item_order_id_normalized`, `item_order_id_adjusted` |
| Line PO (export) | `item_order_id_export` | — |
| Matched PO (header) | `order_id_match` | — |
| Matched PO (line) | `item_order_id_match` | — |
| Matched PO additional field (line) | `item_order_id_match_status` | — |
| Supplier name override | `sender_name_override` | `sender_name_user`, `sender_manual` |

---

## Step 6: MDH Datasets

**Fetch datasets:** For each org in `prd_config.yaml`, call `rossum_set_token` with that org's `api_base`, then `data_storage_list_collections`. Collect results across all orgs and deduplicate.

Format: `{environment}_{use case}_{datasetName}`

- **Environment** — always mandatory, always first (MDH is a shared service; env prefix separates datasets regardless of deployment type)
- **Use case** — mandatory when multiple use cases exist
- **Dataset name** — camelCase, no underscores within it, no numbers
- Entire name lowercase (camelCase uses uppercase only for word boundaries within the dataset name segment)

| Issue | Bad | Good |
|-------|-----|------|
| Environment not first | `corsair_suppliers_test` | `test_corsair_suppliers` |
| Environment not first | `addresses_prod` | `prod_addresses` |
| Underscores in dataset name | `prod_ar_customers_emails` | `prod_ar_customersEmails` |
| Number in dataset name | `prod_suppliers2` | `prod_suppliers` |
| Missing environment | `ar_customers` | `prod_ar_customers` |
| Missing use case (multiple exist) | `prod_suppliers` | `prod_ar_suppliers` |

---

## Output Format

Output the project profile first, then findings grouped by entity type:

```
[WORKSPACE] Acosta [PROD]
  Issue: environment tag present in multi-org deployment
  Suggested: Acosta

[HOOK] Validation Datasets [MDH] [PROD]
  Issue: extension name in square brackets — must use round brackets
  Suggested: Validation Datasets (MDH) [PROD]

[FIELD] v1_match_data  (hook: Validation #1 (MDH) / Contract data - header level / mapping)
  Issue: primary match target must end with _match
  Suggested: v1_match

[FIELD] item_v2_cvp_promotion_id  (hook: Validation #2.2 (MDH) / CVP validation / additional_mapping)
  Issue: additional_mapping target must start with primary match id (item_v2_match_)
  Suggested: item_v2_match_cvp_promotion_id

[DATASET] test_suppliers
  Issue: missing use case (multiple use cases exist)
  Suggested: test_{use_case}_suppliers
```

End with a summary:
```
Summary: X workspace issues, Y queue issues, Z hook issues, W field issues, V dataset issues
```
