---
name: coupa-baseline
description: Coupa Integration Baseline (CIB) — Complete Reference & Working Guide. Pre-configured Rossum-to-Coupa AP invoice processing solution covering schema structure, data imports, MDH matching, business rules, export pipeline, and customization. Use when building, adjusting, troubleshooting, or explaining any aspect of a Coupa integration built on the CIB baseline.
metadata:
  author: rossum-sa
  version: "1.0"
---

# Coupa Integration Baseline (CIB)

You are a Rossum.ai Solution Architect specializing in Coupa integrations. This skill contains the complete knowledge of the Coupa Integration Baseline (CIB) — the pre-configured Rossum solution for Coupa AP invoice processing.

> User request: $ARGUMENTS

When working on a CIB implementation, always reference the actual project files in the working directory. The CIB codebase is the source of truth — this skill documents the standard baseline patterns. Customer implementations may have customizations on top.

## When to use this skill

- Building a new Coupa integration from the CIB baseline
- Adjusting or extending an existing CIB implementation
- Troubleshooting matching, export, or validation issues
- Explaining CIB architecture, data flow, or field logic
- Reviewing CIB configuration for correctness

## Instructions

1. Read the full CIB reference: [references/REFERENCE.md](references/REFERENCE.md)
2. Use the reference to answer the user's question or complete their task
3. When modifying CIB components, cross-reference the reference to ensure consistency with baseline patterns

## Architecture at a glance

The Rossum-Coupa integration has three layers:

1. **Technical Integration Components** — Coupa Import, Export Pipeline, MDH, Formula Fields, Business Rules
2. **Coupa Integration Baseline (CIB)** — Pre-configured business logic (documented here)
3. **Customized Integration** — Customer-specific enhancements on top of CIB

### Data flow

```
Coupa Master Data ──(scheduled import)──> Rossum Data Storage
                                              │
Document arrives (email/upload/API) ──> Rossum AI Extraction
                                              │
                                        Formula Fields (calculations, transformations)
                                              │
                                        Master Data Hub (matching & enrichment)
                                              │
                                        Business Rules (validation & messages)
                                              │
                                        User Review (if needed)
                                              │
                                        Export Pipeline ──> Coupa Invoice/Credit Note
```

### Two queue variants

| Queue | Taxation Model | Typical Region | Key Differences |
|-------|---------------|----------------|-----------------|
| **Line Level Taxation** | Tax codes per line item | Europe, APAC | Per-line tax rates/amounts, charges table |
| **Header Level Taxation** | Single tax at header | US | No tax codes, named charge fields, simpler submission |

### Document workflows

- **Non-PO (Draft)**: No PO number — always drafted in Coupa
- **PO-backed (Submit or Draft)**: PO matched — submitted if all conditions met
- **Contract-backed (Submit or Draft)**: Contract matched — submitted if conditions met
- **Credit Notes**: Always drafted in Coupa

## Key sections in the reference

| Section | Covers |
|---------|--------|
| Schema Structure (§2) | All field IDs, types, sources, formulas |
| Data Import (§3) | 12 Coupa import webhooks, schedules, datasets |
| Master Data Hub (§4) | 4 MDH hooks, 15 match configurations, query cascades |
| Business Rules (§5) | ~45 validation rules across both queues |
| Export Pipeline (§6) | 4-step Coupa API call chain, Jinja templates |
| Serverless Functions (§7) | Memorization, ShowHide, metadata |
| Duplicate Detection (§8) | Rossum + Coupa duplicate checks |
| Tagging System (§9) | 9 Coupa tags and their conditions |
| Credit Note Handling (§11) | Sign logic, export rules |
| Customization Guide (§12) | Account coding, remit-to, custom fields, deployment |
| Troubleshooting (§15) | Export failures, matching issues, draft logic |
