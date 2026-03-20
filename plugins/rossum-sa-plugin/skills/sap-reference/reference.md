# SAP Integration Guide for Rossum

## SAP Product Landscape

### SAP HANA
In-memory, columnar, relational database that runs SAP products.

### SAP ECC 6
Legacy ERP system running on various RDBMS (mainly Oracle). SAP is ending support in 2027 (exceptions to 2030). All prospects/customers are in transition to S4 HANA.

### SAP S4 HANA
Successor of ECC 6. Improved database (HANA). Current and future standard.

### SAP S4 HANA Public Cloud
- Cloud version of S4 HANA with standard APIs (OData, SOAP, REST)
- Standardised version common for all tenants
- Easy to integrate — all APIs available on the internet
- Rossum has generic master data "import" extension and export function (MEGA)
- Almost no customers use this yet — SAP pushes "Clean Core" but most customers have heavy customisations
- **Scoping**: Easy to integrate, APIs are fairly robust. Always review the necessary API(s) before committing.

### SAP S4 HANA Private Cloud
- On-premise version of S4 HANA. Backend is very different from Public Cloud (full DB access, ABAP customisations)
- Migration from ECC is simpler to this version (only option when ECC was customised)
- **Most customers and prospects** want integration with this version
- Integration always requires middleware (good: easier for Rossum via IDOC generation with MEGA; bad: requires customer IT resources)
- Traditional integration: generate IDOC (SAP XML structure per transaction, e.g. ORDERS05, INVOIC02)
- **Scoping**: No other way to integrate with Private Cloud/ECC. Critical questions:
  - What is their IT landscape?
  - Do they already integrate with SAP and how?
  - What middleware tool are they using?
  - As long as they provide a pathway through middleware, Rossum can integrate

### SAP Ariba
Spend management system (procurement, sourcing, supplier management). Not an ERP. Rossum focuses on Coupa instead. APIs differ from native SAP modules.

### SAP Ariba Network
Supplier/Buyer cloud platform for B2B transactions.

### OpenText VIM (Vendor Invoice Management)
- Plugin installed on-prem next to SAP ECC/S4 Private Cloud but exposes internet-facing APIs
- Allows Rossum to integrate directly without middleware
- Competitor in a way (offers poor OCR but superior UI/Workflow to vanilla SAP)

### SAP CIM
SAP's answer to VIM. Early stage, limited capabilities, inferior to VIM.

### SAP BTP (Business Technology Platform)
- Cloud platform with many components; most important: Integration Suite (formerly CPI)
- Integration platform like Mulesoft, Azure Logic Apps, UiPath
- Rarely used by customers (rarely used)

### SAP Cloud Connector
Reverse proxy installed on-prem allowing BTP to connect to on-prem SAP. Rarely used (BTP is rare, S4 supports HTTPS natively).

### SAP Fiori Apps
SAP Web framework for business applications. Used by both Private and Public Cloud. Private cloud also runs SAP GUI and SAP Web GUI (via NetWeaver).

## Master Data

**Biggest pain point** for most customers (aside from Public Cloud where APIs are robust). Without deep SAP/ABAP knowledge, it's difficult to customise master data export or implement deltas.

**Scoping checklist:**
- How will master data exchange happen?
- Do they already produce master data for other systems? If so, get samples.
- Ask about deltas — especially for AR Material Master (100s of thousands of records)

## SAP Customisations

- **Public Cloud**: No customisations (standard workflows, forms, dashboards only)
- **Private Cloud**: Full customisation via ABAP (Advanced Business Application Programming)
  - New data models, RFC-enabled functions, BAPIs
  - **Scoping**: Ask if they have custom tables and can provide them as master data

## AP/AR Terminology

| Term | Description |
|------|-------------|
| FI | Financial Accounting — financial accounting, reporting |
| MM | Material Management — procurement & inventory management |
| GRNIV | Goods Receipt Invoice Validation — validates sufficient received amount for invoice posting. Rossum can do this with GR master data |
| FICO invoice | Non-PO backed invoice (typically INVOIC02 IDOC) |
| MIRO invoice | PO-backed invoice (typically INVOIC02 IDOC) |
| Sales Order | AR — typically ORDERS05 IDOC |

## Rossum-SAP Implementation Examples

| Customer | Integration Pattern | Master Data | Export |
|----------|-------------------|-------------|--------|
| **Customer A** | HTTPS XML API via CPI | Synced by customer via MDH API | Rossum pushes sales order to CPI |
| **Customer B** | SFTP-based | Pulled from same SFTP | IDOCs generated and placed on SFTP |
| **Customer C** | Hybrid | Scheduled Imports extension | Custom serverless function calling VIM Invoice API |
| **Customer D** | SFTP-based | Pulled from same SFTP | IDOCs generated and placed on SFTP |
| **Customer E** | Azure API Manager | Customer's Azure middleware calls MDH API | Rossum generates IDOC XML, pushes via Azure APIM |
