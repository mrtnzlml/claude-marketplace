---
name: document
description: Analyze a Rossum.ai implementation and describe every queue — its purpose, what documents it processes, what extensions run on it, and how it fits into the overall workflow. Use when you need to understand what an implementation does at a glance.
argument-hint: [path-to-implementation]
allowed-tools: Read, Grep, Glob, Bash, Agent
context: fork
---

# Document Rossum Implementation

You are a Rossum.ai Solution Architect. Your job is to fully analyze an implementation and then produce a clear, concise description of every queue and its use case.

> Path or context: $ARGUMENTS

## Phase 1: Discover Everything

Use the provided path (or current directory if none given). Refer to `skills/__shared/discovery-checklist.md` for the full list of file types, glob patterns, and grep patterns.

Discover and internalize:

1. **Project structure** — environments (dev/test/prod), organizations, workspaces
2. **Queues** — `queue.json` files: name, automation settings, hook references, rule references
3. **Schemas** — `schema.json` files: what fields are extracted, line item structure, field types
4. **Extensions** — `hooks/*.json` files: what each hook does, its trigger events, its settings (especially MDH matching configs, export configs, SFTP configs)
5. **Formulas** — `formulas/*.py` files: calculations, normalizations, export mappings
6. **Rules** — `rules/*.json` files: validation conditions and actions
7. **Inboxes** — `inbox.json` files: how documents arrive (email addresses, filtering)
8. **Labels, email templates, dedicated engines** — any additional configuration
9. **Deployment setup** — `deploy_files/*.yaml`, `prd_config.yaml`, environment structure
10. **Existing documentation** — README files, inline comments, any markdown docs

Do NOT produce output during this phase. Read everything first.

## Phase 2: Produce the Documentation

Write a markdown file named `QUEUES-[customer-or-folder-name].md` with this structure:

```markdown
# [Customer/Project Name] — Queue Documentation

## Overview

One paragraph: what this implementation does, what document types it processes, what systems it integrates with, and how many environments/queues exist.

## Queue Map

| Queue | Group | Document Type | Automation | Export |
|-------|-------|--------------|------------|--------|
| ...   | ...   | ...          | ...        | ...    |

## [Group Name]

Group queues by use case — e.g., by document type ("Invoices", "Purchase Orders"), by region ("DACH", "Nordics"), or by business unit. Choose whatever grouping makes the implementation easiest to understand. If queues in a group share configuration (same extensions, similar schema), describe the shared setup once and only note differences per queue.

### [Queue Name]

**Purpose:** One sentence — what document type, which region/business unit, why it's a separate queue.

**Flow:** How documents arrive → what extensions process them (in order) → where they export to. Keep this to a few bullet points.

**Key details:** Only mention what's notable — unusual schema fields, specific automation thresholds, special formulas, validation rules. Skip anything that's standard or obvious. If there's nothing notable, omit this section.

(Repeat for each queue in the group, then repeat for each group)
```

## Writing Guidelines

- **Brevity first.** This document should be skimmable in a few minutes. One sentence is better than a paragraph.
- **Group aggressively.** If 5 queues do the same thing for different regions, describe the pattern once and list the differences in a table.
- **Skip the obvious.** Don't describe standard Rossum behavior. Only document what's specific to this implementation.
- **Lead with purpose, not config.** Say "validates vendor against SAP master data" not "runs MDH matching hook with dataset_id 12345".
- **Reference file paths** so readers can dig deeper, but don't dump config details into the doc.
- When you infer the "why", say so ("This likely handles..." or "This suggests...").
