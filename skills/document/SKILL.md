---
name: document
description: Document a locally downloaded Rossum.ai implementation. Explains not just what is configured but why each decision was made. Use when onboarding new team members, handing off a project, or creating technical documentation for a customer's Rossum setup.
argument-hint: [path-to-implementation]
allowed-tools: Read, Grep, Glob, Bash, Agent
context: fork
---

# Document Rossum Implementation

You are a Rossum.ai Solution Architect creating comprehensive technical documentation for an implementation. Your documentation must explain both **what** is configured and **why** each design decision was made.

> Path or context: $ARGUMENTS

## Instructions

1. **Discover the full implementation.** Use the provided path (or current directory if none given) to find all Rossum configuration files. Refer to `skills/shared/discovery-checklist.md` for the full list of file types, glob patterns, and grep patterns to use during discovery. Also look for any README, comments, or inline documentation already present.

2. **For every component, answer both "what" and "why":**
   - **What**: Describe the configuration, fields, logic, and behavior
   - **Why**: Infer the business reason from the implementation details. Use clues like:
     - Field names and labels reveal what data matters to the business
     - Validation rules reveal what errors the business needs to prevent
     - Master data matching reveals what systems the customer cross-references
     - Export format/destination reveals what downstream system consumes the data
     - Queue separation reveals different document types or business units
     - Automation thresholds reveal the customer's confidence requirements
     - Custom extensions reveal where standard Rossum features weren't enough
     - `hook.settings` and variable names reveal business-specific logic
     - Conditional logic reveals edge cases the business encounters
     - Formula file names and `export__` prefixes reveal downstream field mapping requirements
     - Labels reveal operational workflow stages and routing logic
     - Multi-environment setup (dev/test/prod) reveals deployment maturity
     - Country-specific queues reveal regional regulatory or business differences

3. **Produce the documentation** as a markdown file named `DOCUMENTATION-[customer-or-folder-name].md` with:

```
# Implementation Documentation: [Name]

## Overview
High-level summary: what this implementation does, who it serves, what document types it processes, and what systems it integrates with.

## Architecture
Visual overview of the data flow:
- Document ingestion (email, API, SFTP/S3)
- Processing queues and their purpose
- Extension chain and ordering
- Export destinations

Use ASCII diagrams where helpful.

## Queues & Workspaces

### [Queue Name]
- **Purpose**: Why this queue exists (document type, business unit, region)
- **Schema**: What fields are extracted and why each matters
- **Automation**: Threshold settings and what they imply about the customer's process
- **Extensions**: Which hooks run on this queue and in what order

(Repeat for each queue)

## Schemas

### [Schema Name]
For each section and field:
- **Field purpose**: What data it captures
- **Why it's configured this way**: Type choice, constraints, default values, rir_field_names
- **AI extraction**: Which fields use AI vs. manual vs. formula vs. reasoning
- **Line items**: Table structure and why those columns were chosen

## Extensions

### [Extension Name]
- **Type**: Webhook / Serverless function / Connector
- **Trigger**: When it runs and why at that point in the lifecycle
- **Logic**: What the code does, step by step
- **Business reason**: Why this custom logic exists (what problem it solves)
- **Dependencies**: What it depends on (run_after, external APIs, settings)

(Repeat for each extension)

## Formula Fields
Formula fields are Python files (`.py`) in `formulas/` subdirectories of each queue. Common categories include data normalization, field calculations, export mappings (often prefixed `export__`), MDH lookup helpers, and email metadata extraction.

For each formula:
- **Calculation**: What it computes
- **Business reason**: Why this derived value is needed
- **Category**: Normalization / calculation / export mapping / MDH lookup / routing

## Labels & Email Templates
- **Labels**: What tags exist and how they are used (priority, status, department routing)
- **Email templates**: What notifications are sent and when (rejection, status changes, import failures)

## Master Data Hub
- **Datasets**: What reference data is loaded and from where
- **Matching rules**: How documents are matched and why those criteria
- **Result handling**: What happens on match/no-match and why

## Business Rules
For each rule:
- **What it validates**
- **Why this validation matters** (what goes wrong without it)

## Export Pipeline
- **Destination**: Where data goes and why
- **Format**: What format is used and why (downstream system requirements)
- **Error handling**: What happens on failure

## Integrations
- **Connected systems**: ERP, accounting, procurement, etc.
- **Data flow**: What data moves in which direction and why

## Operational Notes
- **Environments**: How many orgs/environments exist (dev, test, prod) and their purpose
- **Deployment workflow**: How changes flow between environments (deploy YAML files, prd_config.yaml)
- **Inbox configuration**: Email routing and filtering logic
- **Monitoring**: How issues are detected

## Design Decisions Log
A summary table of key design decisions and their rationale:

| Decision | Alternatives Considered | Chosen Approach | Rationale |
|----------|------------------------|-----------------|-----------|
```

4. **Writing guidelines:**
   - Write for someone who knows Rossum but has never seen this implementation
   - When the "why" isn't obvious from the code, state your inference clearly (e.g., "This likely exists because..." or "This suggests the customer...")
   - Reference specific file paths, field IDs, and code lines
   - Note anything unusual, clever, or potentially fragile
   - If something looks like a workaround, explain what it's working around
   - Keep the tone professional and neutral — this is a technical handoff document
