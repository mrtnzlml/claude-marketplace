# SKILL: Document Processing for Transactional Workflows

## Purpose
Extract structured data from invoices, purchase orders, receipts, and other transactional documents. Validate, transform, and route the data to downstream systems.

## Instructions
- Accept uploaded documents (PDF, image, email attachment) and extract all key fields
- For invoices: extract vendor name, invoice number, date, line items, amounts, tax, currency, PO reference, payment terms, bank details
- For purchase orders: extract buyer, supplier, line items, quantities, unit prices, delivery dates
- For receipts: extract merchant, date, items, totals, payment method
- Cross-validate extracted fields (e.g., line item totals vs. grand total, tax calculations)
- Flag anomalies: duplicate invoice numbers, amounts exceeding thresholds, missing fields
- Output structured JSON matching the user's ERP schema
- Support multi-language documents (infer language automatically)
- Handle poor scan quality by noting confidence levels per field
- Learn user corrections: if a user fixes a field, remember that vendor's format for next time
- Provide a summary of each batch: documents processed, exceptions flagged, confidence distribution

## Output Format
Return a structured JSON object per document with extracted fields, confidence scores, and validation flags.

## Integrations
User can paste or upload documents. Output JSON can be copied to clipboard or saved for ERP import.
