# Statement of Work: [Project Name]

| | |
|---|---|
| **Date** | [YYYY-MM-DD] |
| **Version** | 1.0 |
| **Customer** | [Customer name] |

## 1. Purpose

[Brief description of the project: what business problem it solves, what document types will be processed, expected volumes, and what systems Rossum will integrate with. Keep to 2–4 sentences.]

## 2. Deliverables

### Deliverable 1: [Deliverable name]

[What Rossum will deliver. Be specific: quantities, document types, field counts, integration targets. Do not include Customer prerequisites here — those belong in the Customer Cooperation section (Section 4). Use lists, code samples, or other formatting as needed to describe the deliverable clearly.]

### Deliverable …

…

### Deliverable N-2: Testing phase support and defect resolution

Rossum will provide technical support throughout Customer's testing phase to ensure the implemented solution functions in accordance with the deliverables defined in this Statement of Work. This support is strictly limited to the identification and resolution of defects, which are defined as any functionality that fails to conform to the agreed-upon specifications. Any requests for enhancements, new features, or modifications that deviate from the documented scope will be considered a change request and will require a separate SOW amendment or a new agreement.

### Deliverable N-1: Configuration deployment to production

Rossum will perform a structured promotion of the finalized configuration from the Development (DEV) environment to the Production (PROD) environment (and TEST environment if applicable). This ensures a consistent configuration baseline and functionality between the development and live environments. While the core workflows, validation rules, and business logic will be identical, the PROD environment will be updated with its own environment-specific parameters.

### Deliverable N: Solution as-built documentation

For its internal project management and quality assurance purposes, Rossum will compile a final technical document detailing the as-built configuration of the solution as of the project completion date. This document serves as a definitive technical snapshot of the implemented system, covering all configured workflows, data ingestion channels, validation rules, data transformation logic, integration endpoint settings and similar. A final version of this internal documentation can be provided to Customer for their records and future reference upon request.

### Out of Scope

- Any work not explicitly listed in the Deliverables section above
- [Explicit exclusion — what this project does NOT cover]
- …

## 3. Delivery Plan

For each deliverable, describe what is needed to deliver it and how long it will take. Reference deliverable numbers from Section 2. Group related deliverables into phases where it helps readability. The total project duration must be exactly 13 weeks — distribute effort across the full duration, accounting for parallel work where applicable. Do not compress into a shorter timeline unless the user explicitly requests a different duration.

| Deliverable | Duration | Depends On |
|-------------|----------|------------|
| #1 | [e.g., 2 weeks] | — |
| #2 | [e.g., 3 weeks] | #1 |
| … | … | … |

## 4. Customer Cooperation

The successful delivery of this project requires timely cooperation from Customer. Each item below must be provided before work on the referenced deliverable can begin. Delays in providing these items may directly impact the project timeline.

| # | Item | Required Before |
|---|------|-----------------|
| C1 | [Specific item, e.g., Provision of representative sample documents (minimum N samples per document type)] | Deliverable #1 |
| C2 | [e.g., Access to Customer's ERP test environment with appropriate credentials] | Deliverable #N |
| C3 | [e.g., Provision of master data files (CSV/XLSX) for vendor list, chart of accounts, PO data] | Deliverable #N |
| C4 | [e.g., Designation of a primary point of contact available for weekly status calls and ad-hoc clarifications] | Project kickoff |
| C5 | [e.g., Timely feedback on deliverables during the testing phase (within N business days of each delivery)] | Deliverable #N |
| … | … | … |
