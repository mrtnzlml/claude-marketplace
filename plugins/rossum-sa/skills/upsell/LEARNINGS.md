# Upsell Skill Learnings

## DOs

- **Check MDH JMESPath field names against actual Data Storage documents.** MDH matching cascades can return results from multiple collections (e.g., a memorization collection AND a master dataset). Always verify that the JMESPath expression works for every collection in the cascade — memorization collections often have different field names than the primary dataset (e.g., `_id` only, no `id`; `sender_match` instead of `VendorNumber`). Use `data_storage_find` to sample each collection involved in the cascade before recommending a fix.

- **When `remit-to-addresses` (or similar nested Coupa fields) appear in a JMESPath result mapping, check whether the field is an array or an object.** In `suppliers_prod`, `remit-to-addresses` is an array — direct property access like `"remit-to-addresses"."remit-to-code"` will always fail. The correct form is `"remit-to-addresses"[0]."remit-to-code"`. Also check for null/empty array cases and recommend null-safe fallback expressions.

- **Always check for `automation_disabled` at annotation level as a primary blocker.** 100% `automation_disabled` across a queue almost always means automation was never switched on at the queue level after a TEST→PROD migration, not a hook-level issue. Distinguish it from extension-type blockers before diagnosing hooks.

- **Look at `_memorization_*` collections alongside primary datasets when diagnosing MDH match failures.** Memorization records store a minimal structure (sender_name, sender_address, sender_match, annotation_id, created_at) and do not carry the rich fields (VendorNumber, id, etc.) that primary dataset records do. If a hook reads a field that only exists in the primary dataset, it will fail silently when a memorization record wins the cascade.

- **When `item_rate_calc` shows both high `error_message` and high `no_validation_sources` blockers on the same queue, treat them as two separate issues requiring two separate fixes.** The `no_validation_sources` status means the validation source is not configured at all (configuration gap, often from a missed setup step during queue launch). The `error_message` blocker ("VAT Rate cannot be empty") is a formula logic issue that fires when the line item has no VAT rate even if the validation source is configured. Fixing one does not fix the other — both must be addressed independently.

- **When `item_rate_calc` formula errors affect multiple queues at varying rates (8–57%), check whether each queue's invoices carry VAT rates at the line-item level or only at the header/tax-detail level.** The formula fails silently on invoices where suppliers print VAT only at the header level. The formula should be updated to propagate the header-level VAT rate to line items or return null rather than a blocking error. Confirm the dominant invoice structure per queue using sample documents before recommending a single fallback strategy.

- **When a queue shows near-zero automation (< 5%) and was launched recently (< 6 months), treat it as a multi-factor failure requiring a structured investigation across formula configuration, validation sources, hook settings, and AI training data.** Do not diagnose from blocker percentages alone — individual blockers often cascade (e.g., missing validation source → formula error → item_amount_total cascade). Sequence the fixes: configuration gaps first, then formula logic, then hook tuning, then training assessment.

- **When a hook returns HTTP 422 "Failed to update additional mappings. Make sure no other extension updates the target matching datapoint before matching is run", the issue is a hook execution ordering race condition — not a data or schema problem.** The fix can be either hook priority/ordering or user is deleting drop down value of the matched field.

- **When duplicate-handling extension returns "body.document.s3_name: Input should be a valid string", the document was submitted without file metadata — not a hook bug.** Commonly happens on API-uploaded documents. The fix is null-safe handling in the extension, not changes to the submission flow.

- **When a field shows `error_message` blocker on 90%+ of a queue, check first if it is a required export field with no population logic.** A missing formula or hook assignment rather than a formula error is more likely at that occurrence rate. Confirm by looking at automation attempt logs ("Trying to automate") for `type: error, content: required`.

## DON'Ts

- **Do not suggest fixing SSL certificate issues on Rossum-hosted extensions as a project team deliverable.** SSL certificate renewal for extensions hosted on `*.rossum-ext.app` or similar infrastructure is an infrastructure-level concern, not something the implementation project team can resolve through configuration. Flag it as an infrastructure ticket, not a SOW item.

- **Do not suggest reducing or eliminating API rate-limiting (HTTP 429) as an improvement.** Rate limiting is a platform-level infrastructure behaviour that cannot be disabled or adjusted through configuration. Multiple hooks hitting 429 during batch events is expected behaviour. Do not recommend it as an actionable fix — instead, note that it is transient and self-resolving, and only escalate if it is systematic and persistent rather than burst-related.

- **Do not suggest expanding master data datasets (suppliers, vendors, etc.) as a Rossum deliverable.** Adding or updating entities such as suppliers, vendors, or cost centres in master data is the responsibility of the external source system (e.g., Coupa, ERP). Rossum's MDH import hooks sync whatever the source system exposes — if a supplier is missing from MDH, it is because it is missing or inactive in the source system. Recommend that the Customer review and correct the source system data, not that Rossum adds records manually.
