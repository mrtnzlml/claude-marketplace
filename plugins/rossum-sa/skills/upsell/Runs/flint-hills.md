# Automation Analysis Report — Flint Hill Resources (Org 415098)

**Period:** Feb 23 – Apr 23, 2026 | **Cluster:** prod-us2 | **Base URL:** https://flint-hill-resources.rossum.app

---

## Queue Overview

| Queue | Workspace | Documents | Automation Rate |
|---|---|---|---|
| Invoices (2899674) | Coupa Integration Baseline | 281 | **0%** |
| Split Documents (2899673) | Splitting & Classification | 116 | **0%** |
| 01 Inbox (2899672) | Splitting & Classification | 4 | **0%** |

---

## Findings & Recommendations

| # | Suggestion | Category | Impact | Effort | Affected |
|---|---|---|---|---|---|
| 1 | **Enable Autopilot on all queues** | TAM | Critical | Low | All queues |
| 2 | **Fix Coupa PO Line import failures** | SA | High | Medium | Queue 2899674 |
| 3 | **Investigate & fix MDH ReadTimeout on sender match** | SA | High | Medium | Queue 2899674, Hook 1151812 |
| 4 | **Resolve supplier mismatch (sender_match errors)** | SA | High | Medium | Queue 2899674 |
| 5 | **Fix line item amount calculation errors** | SA | Medium | Medium | Queue 2899674, Hook 1151824 |
| 6 | **Fix recipient_match failures** | SA | Medium | Medium | Queue 2899674 |
| 7 | **Improve PO number (order_id) extraction confidence** | SA | Medium | Medium | Queue 2899674 |
| 8 | **Address closed PO/PO line handling** | TAM | Medium | Low | Queue 2899674 |
| 9 | **Improve AI training for core header/line fields** | TAM | Medium | Medium | Queue 2899674 |
| 10 | **Improve document_type classification confidence** | SA | Medium | Low | Queue 2899673 |

---

## Detailed Descriptions

---

### 1. Enable Autopilot on All Queues *(TAM)*

**Observation:** 100% of annotations across all three queues carry the `automation_disabled` blocker at annotation level. Per platform behaviour, this means the autopilot toggle was never switched on at the queue level — most likely after the initial deployment. No document can auto-export regardless of field quality or matching results. This single configuration gap is blocking all measured automation.

**Affected:** Queues 2899672, 2899673, 2899674

---

### 2. Fix Coupa PO Line Import Failures *(SA)*

**Observation:** Kibana logs show recurring `missing_digest_index` and `import_terminated` events for the `purchase_order_lines` dataset throughout the 60-day window (observed Apr 13–15 and earlier). The import worker fetches PO lines from Coupa (`fhr.coupahost.com`) using a full replace strategy with `updated-at[gt_or_eq]=1970-01-01` — fetching the complete dataset every time. Multiple runs are being terminated mid-flight before the replace completes, leaving MDH with stale or incomplete PO line data. This is a direct root cause of the `item_order_item_match` failures (33.8% of invoices, 95 documents): the matching hook cannot find the PO line in MDH because the import never finished replacing the dataset cleanly.

The same `missing_digest_index` pattern was observed on Apr 13 for `suppliers`, `addresses`, `payment_terms`, `tax_registrations`, `account_types`, and `lookup_values`, suggesting a broader one-day import disruption that may have partially corrupted multiple datasets.

**Affected:** Queue 2899674, `long-running-jobs-workers-coupa`, datasets: `purchase_order_lines`, `suppliers`, `addresses`, `payment_terms`

---

### 3. Investigate & Fix MDH ReadTimeout on Sender Match *(SA)*

**Observation:** 34 `ReadTimeout` errors were recorded over 60 days for hook 1151812 calling `https://flint-hill-resources.rossum.app/svc/master-data-hub/api/v1/match`. The hook exceeds the 30-second timeout. This prevents supplier matching from running on affected documents and may contribute indirectly to the `sender_match` blocker rate. Root cause could be slow MDH query execution on the suppliers dataset (large collection, unoptimized query) or resource contention during parallel import runs.

**Affected:** Queue 2899674, Hook 1151812

---

### 4. Resolve Supplier Mismatch (sender_match Errors) *(SA)*

**Observation:** Hook 1151824 (business rules) logs show the message *"The Supplier on the backing document PO/Contract is different from the Supplier matched on the document"* on 30.9% of invoices (87 docs). MDH successfully matches a supplier to the invoice, but that supplier does not match the supplier recorded on the referenced PO in Coupa. Possible causes: (a) invoices from sub-suppliers or remit-to entities that differ from the contracting supplier in Coupa, (b) MDH memorization records winning the cascade with a different supplier than the PO expects, or (c) the `sender_name_export` field (affecting 29 docs, 10.3%) pulling an incorrect display name. Requires deeper investigation into the MDH cascade configuration and JMESPath field mappings.

**Affected:** Queue 2899674, Hook 1151824, MDH `suppliers` / `_memorization_*` collections

---

### 5. Fix Line Item Amount Calculation Errors *(SA)*

**Observation:** 15.3% of invoices (43 docs) show `item_amount_base`, `item_amount_base_calculated`, `item_price_export`, `item_total_base`, and `item_total_base_calculated` simultaneously blocked with `error_message`. Hook 1151824 logs show *"required"* appearing 14+ times on a single annotation — every line item amount field flagged as empty. A separate group shows *"The Total Amount is different from the Total that will be calculated in Coupa"* on `coupa_total_calculated` and `amount_total_base_calculated` (91 and 73 docs with extension blockers respectively). These are two distinct issues: (a) line items arriving with missing amounts (non-standard invoice formats), and (b) a total reconciliation mismatch between what Rossum calculates and what Coupa expects.

**Affected:** Queue 2899674, Hook 1151824

---

### 6. Fix Recipient Match Failures *(SA)*

**Observation:** 12.1% of invoices (34 docs) are blocked on `recipient_match` with error messages. A further 13 docs (4.6%) are blocked on `recipient_name_export`. The recipient entity (buyer/company) is either not matching in MDH or returning an export mapping error. Requires investigation into the MDH entity/addresses dataset and whether the company lookup correctly covers all legal entities used by Flint Hill Resources.

**Affected:** Queue 2899674, Hook 1151824

---

### 7. Improve PO Number (order_id) Extraction Confidence *(SA)*

**Observation:** `order_id` (PO number) has a mean extraction confidence of 83.3%, but only 0.37% of documents pass the automation threshold — 99.6% of all documents fail the low_score check for this field. This extreme discrepancy suggests the automation threshold is set much higher than the engine's typical output, or that the field format varies significantly across suppliers. Since `item_order_item_match` depends on a correctly extracted PO number, this is a compounding issue: even when a PO line exists in MDH, the match may fail if the extracted PO number is below threshold. A threshold tuning exercise and review of accepted value formats is warranted.

**Affected:** Queue 2899674

---

### 8. Address Closed PO / PO Line Handling *(TAM)*

**Observation:** Multiple annotations are blocked by *"The PO is closed"* and *"The PO line is closed"* errors from hook 1151824. These invoices reference POs that Coupa has already fully received or closed. This is a business process question: should invoices against closed POs be hard-blocked and sent to review, or should they be allowed through with a warning flag for AP to decide? If the volume of closed-PO invoices is expected to remain, adjusting the business rule to a soft warning rather than a blocking `error_message` could recover some automation.

**Affected:** Queue 2899674, Hook 1151824

---

### 9. Improve AI Training for Core Header & Line Fields *(TAM)*

**Observation:** Several core extraction fields show systemically low automation rates despite moderate-to-high mean confidence, indicating the AI model needs more training data:

| Field | Low Score Rate | Automation Rate | Mean Confidence |
|---|---|---|---|
| `order_id` | 99.6% | 0.4% | 83.3% |
| `sender_name` | 96.1% | 3.9% | 84.1% |
| `item_quantity` | 85.8% | 3.5% | 84.1% |
| `item_description` | 83.3% | 15.2% | 82.4% |
| `item_code` | 66.5% | 5.5% | 75.9% |
| `currency` | 65.1% | 34.2% | 92.7% |
| `sender_address` | 88.6% | 8.6% | 88.9% |

With 281 processed documents, there should be sufficient confirmed annotations to initiate a targeted training cycle. `currency` in particular may benefit from threshold adjustment given its very high confidence mean.

**Affected:** Queue 2899674

---

### 10. Improve Document Type Classification Confidence *(SA/TAM)*

**Observation:** In the Split Documents queue, `document_type` classification succeeds at ~59.5% automation (mean confidence 0.817), but 40.5% of documents (47 out of 116) fall below the confidence threshold. If documents are misclassified or held in review, they do not flow through to the Invoices queue correctly. Reviewing whether additional document types need to be trained (e.g. credit notes, delivery notes arriving mixed with invoices) could improve throughput.

**Affected:** Queue 2899673

---

## Summary

The most immediately impactful action — requiring no development — is **enabling autopilot on all three queues** (item 1, TAM). The two biggest automation killers after that are the **PO line import failures** corrupting MDH data (item 2, SA) and **MDH timeouts on supplier matching** (item 3, SA). Together these three items account for the majority of blocked documents.

Once autopilot is enabled and import stability is restored, realistic near-term automation potential on the Invoices queue is estimated at 40–60%, subject to resolving the supplier mismatch and field confidence issues.