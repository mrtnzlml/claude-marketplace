# Rossum Project Technical Documentation Guide

When asked to generate technical documentation for a Rossum project (for Confluence, project closure, support handoff, etc.), follow this process.

## Step 1: Explore the Codebase

Use an **Explore subagent** to thoroughly read:

| What to Read | Where |
|---|---|
| All hook configs | `sandbox/<env>/hooks/*.json` |
| Workspace/queue structure | `sandbox/<env>/workspaces/*/queues/*/queue.json` |
| Schema definitions | `sandbox/<env>/workspaces/*/queues/*/schema.json` |
| Formula calculations | `sandbox/<env>/workspaces/*/queues/*/formulas/*.py` |
| Utility scripts | Project root (`*.py`, `*.sh`) |

**Subagent prompt template:**
> Explore the codebase to find ALL files related to: hooks, serverless functions, schemas, formulas, queue configs, and utility scripts. For each file, read its contents and summarize: what it does, its configuration, how it fits into the processing pipeline. Look for mentions of: SFTP, XML, TIFF, PDF, flat file, SAP, Coupa, export, MDH, memorization, duplicate, business rules, validation.

## Step 2: Map the Processing Pipeline

From the hook JSON files, extract:
- **Event types**: `annotation_content.initialize`, `updated`, `confirm`, `export`
- **Execution order**: `run_after` dependencies between hooks
- **Conditional gates**: `condition_actions` fields
- **Queue assignments**: which hooks run on which queues

Draw the pipeline as a sequential + parallel flow showing hook execution order.

## Step 3: Document Structure Template

Use this structure for the output Markdown file:

```
# {Project Name}: Technical Documentation

> Project / Platform / Status / Last Updated / Author metadata block

## Table of Contents

## 1. Project Overview
- What the project does (1-2 paragraphs)
- Key workspaces table (name, ID, purpose)

## 2. Architecture & Processing Pipeline
- Document lifecycle (ingestion → extraction → enrichment → review → export)
- Export pipeline diagram showing hook execution order with IDs
- Parallel vs sequential flows

## 3. Workspaces & Queues
- Table per workspace: queue name, ID, purpose
- Number of hooks per queue

## 4-6. Core Processing Hooks (one section each)
For each major serverless function:
- Hook name, ID, type, event, memory, timeout
- What it does (step by step)
- File format specification (if generating files)
- Country/region-specific variations
- Configuration parameters
- Size/performance optimization details

## 7. ERP Integration (Coupa/SAP)
- Authentication method (OAuth, API key, etc.)
- Sequential hook chain with IDs
- Conditional execution gates
- Error handling

## 8. Master Data Hub (MDH)
- Hook details
- Data collections table
- Matching strategies (exact, fuzzy, memorized, fallback)
- Coupa/SAP data import webhooks

## 9. Business Rules & Validation
- Hook table (name, ID, scope)
- Validations performed (bullet list)

## 10. Duplicate Detection
- Matching criteria
- MongoDB query example

## 11. Memorization Hooks
- Table of memorization hooks (name, ID, purpose)

## 12. Schema & Formula Calculations
- Core field groups table
- Python formula code with explanation for each

## 13. External System Integration (SFTP, APIs)
- Connection details table
- Authentication methods
- File types uploaded

## 14. Idempotency & State Management
- State flag values table
- Duplicate prevention mechanisms

## 15. Error Handling & Edge Cases
- Tables per subsystem: issue → handling

## 16. Utility Scripts
- Script name, purpose, usage example

## 17. Configuration & Secrets
- Plaintext settings table
- Encrypted secrets table

## 18. Legacy System Mapping (if replacing legacy)
- Table: legacy feature → new implementation → hook ID

## 19. Troubleshooting Guide
- Common issues with check/fix steps
- Hook execution order debugging
- Logs & debugging tips

## Appendix: Complete Hook Inventory
- Full table: hook name, ID, type, event
```

## Step 4: Key Details to Capture

For each **serverless function / Lambda hook**, always document:
- Memory and timeout settings
- Third-party library packs used
- Input/output format specs (encoding, delimiters, structure)
- Country/region-specific variations in field ordering or naming
- Size optimization strategies (if applicable)
- Idempotency mechanism (how it prevents duplicate processing)

For each **webhook integration**, always document:
- Auth method and token management
- Request/response format
- Conditional execution gates
- Error parsing and user-facing messages

For **SFTP integrations**, always document:
- Host, port, directory
- Auth options (password vs SSH key)
- File naming conventions
- Remote directory creation behavior

## Step 5: Output

- Write as a single `.md` file in `docs/` directory
- Use tables extensively for scannable reference
- Include code blocks for queries, XML structures, formulas
- Keep language support-team friendly (not developer-only)
- Add a troubleshooting section with actionable steps

## Sections to Skip

Omit sections that don't apply to the project. For example:
- No SAP integration? Skip that section
- No SFTP/file generation? Skip those sections
- No legacy replacement? Skip the mapping table
