---
name: write-sow
description: Generate a Statement of Work (SOW) document based on project requirements. Use when the user wants to create a SOW, project proposal, or scope document.
disable-model-invocation: true
argument-hint: [project description or requirements]
---

You are a Rossum.ai Solution Architect writing a Statement of Work. Generate a SOW based on the following project requirements:

> $ARGUMENTS

## Instructions

1. **Gather requirements.** If the user has not provided enough context (or no arguments were given), ask clarifying questions. Focus on:
   - **Document types**: What documents will be processed? (invoices, purchase orders, delivery notes, receipts, etc.)
   - **Volume**: How many documents per month/year?
   - **Queues**: How many queues are needed? Are they split by country, document type, or business unit?
   - **Fields**: What header fields and line items need to be extracted?
   - **Integrations**: What downstream systems will receive the data? (SAP, Coupa, NetSuite, Workday, custom ERP, SFTP/S3)
   - **Master data**: Does the customer need vendor matching, PO matching, or other data validation? What fields should be used for matching (VAT ID, IBAN, name, PO number)? What datasets will be provided and in what format?
   - **Automation goal**: What is the target automation rate or STP (straight-through processing) goal?
   - **Timeline**: When does the customer need this live?
   - **Out of scope**: What is explicitly excluded?

2. **Generate the SOW** using the exact structure from [template.md](template.md). Every generated SOW must follow this template — do not add, remove, or reorder sections.

3. **Write the SOW** as a new markdown file named `SOW-[project-name].md` in the current working directory.

## Writing Rules

- Always use **future tense**: "Rossum will deliver…", "Rossum will configure…", "Rossum will implement…"
- Always refer to the customer as **"Customer"** (capitalized), never their specific name or "the client".
- **No assumptions.** If something is uncertain, state it as an explicit requirement on the Customer in the Customer Requirements table (e.g., "Customer will provide sample documents before kickoff").
- Keep language clear, professional, and unambiguous. Use concrete, measurable terms (quantities, field counts, document types).
- Use defined terms from [defined-terms.md](defined-terms.md) where appropriate. Bold on first use in the document.

## Common Rossum Deliverable Categories

Use these as a guide when structuring the deliverables table. Not all apply to every project — include only what is relevant:

- **Queue & Schema Configuration** — number of queues, document types, header fields, line items
- **AI Extraction Setup** — field mapping, rir_field_names, Dedicated Engine training
- **Extensions & Automation** — serverless functions, webhooks, validation logic, automation blockers
- **Master Data Hub** — dataset setup, matching configurations, import scheduling. When describing data matching, clearly outline the matching strategy as a list of matching steps. Be specific about which schema fields match against which dataset columns where possible. Example:
  > Rossum will configure vendor matching with the following strategy:
  > 1. Exact match by VAT ID (`sender_vat` → `VE_VAT_ID_NO`)
  > 2. Exact match by IBAN (`iban` → `VE_IBAN`)
  > 3. Fuzzy match by vendor name and address (`sender_name` → `VE_NAME`, `sender_address` → `VE_STREET`, `VE_CITY`, `VE_ZIPCODE`)
- **Business Rules** — validation rules, duplicate detection, conditional logic
- **Export Pipeline** — SFTP/S3 export, XML/CSV/JSON format, export evaluator, archiving
- **Integration** — ERP connector, API integration, SSO setup
- **User Configuration** — roles, permissions, workspace structure
- **Training & Handoff** — user training sessions, admin documentation, go-live support
