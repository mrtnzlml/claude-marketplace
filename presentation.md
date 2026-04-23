# Hackathon Presentation: Busman — The Commercial Director

> Team: Busman · Track: Existing Customer Upsell Predictor (Proactive Governance)  
> Date: 2026-04-23

---

## 1. The Problem We Solved

**The gap:** Rossum SAs have deep visibility into customer deployments, but that knowledge rarely reaches the commercial team in time — or in the right language.

Stable accounts (no escalation, no active project) get ignored. But they are often silently degrading:
- Automation rates that were never switched on after go-live
- Hook failures nobody is looking at
- Features paid for but unused
- Configurations inherited from old project decisions

The result: revenue that sits on the table until churn makes it visible.

---

## 2. Our Solution

### What We Built

Three interconnected Claude Code skills that turn a live Rossum environment into a ranked, evidence-backed list of commercial opportunities — and then write the SoW to close them.

```
upsell  →  analyze-kibana-logs  →  analyze-org-for-upsell  →  write-sow
```

| Skill | What it does |
|---|---|
| `upsell` | End-to-end driver: interrogates the Rossum API for automation blockers, delegates to Kibana for log evidence, then auto-generates a Priority Matrix and SoW. Self-improving — writes DOs/DON'Ts back into its own LEARNINGS.md after each run. |
| `analyze-kibana-logs` | Queries Elasticsearch via Teleport mTLS to surface hook failures, error volumes, and processing anomalies without leaving the SA's terminal. |
| `analyze-org-for-upsell` | Scores a live org against 14 upsell signals (MDH coverage, export automation, deprecated extensions, duplicate detection, adoption breadth, …). Produces a ranked markdown report grounded in specific queue/hook IDs. |

### The Priority Matrix Output

Every run produces findings categorised across two axes:

- **Who owns the fix:** SA (technical changes) vs. TAM (process/threshold tuning)
- **Urgency:** P1 Critical → P3 Tech Debt

This lands directly in the hands of the right person, in commercial language, ready to become a line in a SoW.

---

## 3. What the Skill Actually Found (Evidence from Real Runs)

> **Client: Flint Hill Resources · Org 415098 · prod-us2**  
> Period: Feb 23 – Apr 23, 2026 · 401 documents across 3 queues

### Queue Snapshot

| Queue | Documents | Automation Rate |
|---|---|---|
| Invoices (2899674) | 281 | **0%** |
| Split Documents (2899673) | 116 | **0%** |
| 01 Inbox (2899672) | 4 | **0%** |

Zero automation on a live production customer. The skill surfaced 10 ranked findings in a single session.

---

**Finding 1 — Autopilot never switched on (TAM · Critical · Low effort)**  
100% of annotations across all three queues carry the `automation_disabled` blocker. Autopilot was simply never enabled after go-live — not a hook failure, not a data quality issue. Single configuration change. Zero development effort. Immediately recoverable automation.

**Finding 2 — MDH import terminating mid-flight, corrupting PO line data (SA · High · Medium effort)**  
Kibana logs show recurring `missing_digest_index` and `import_terminated` events for the `purchase_order_lines` dataset on Apr 13–15. The Coupa import worker fetches the entire dataset every run using a full-replace strategy — and is being killed before the replace completes. Result: MDH holds stale PO line data, causing `item_order_item_match` to fail on 33.8% of invoices (95 documents). The skill traced the root cause through Kibana → MDH import config → field-level blockers automatically. The same Apr 13 disruption also hit `suppliers`, `addresses`, `payment_terms`, `tax_registrations`, `account_types`, and `lookup_values` — a broader MDH corruption event that would have been invisible without log analysis.

**Finding 3 — MDH ReadTimeout blocking supplier match (SA · High · Medium effort)**  
34 `ReadTimeout` errors in 60 days on Hook 1151812 calling the MDH match endpoint. The hook exceeds the 30-second timeout on the `suppliers` collection — likely due to an unoptimised query or resource contention during parallel import runs. Identified to the specific hook ID and API call. Not guesswork.

**Finding 4 — Supplier mismatch on 30.9% of invoices (SA · High · Medium effort)**  
Hook 1151824 logs the message *"The Supplier on the backing document PO/Contract is different from the Supplier matched on the document"* on 87 documents. MDH finds a supplier match, but that supplier doesn't match the one on the referenced PO in Coupa. Three candidate causes identified: sub-supplier / remit-to entities, MDH memorization cascade winning with the wrong record, or incorrect `sender_name_export` field mapping. Scoped to Hook 1151824 and the `suppliers` / `_memorization_*` MDH collections — ready for an SA to investigate.

**Finding 5 — PO number threshold misconfigured: 83% confidence, 0.4% automation (TAM · Medium · Low effort)**  
`order_id` extraction averages 83.3% confidence but passes automation on only 0.4% of documents (99.6% fail the `low_score` check). The automation threshold is set far above what the engine delivers. A threshold tuning exercise would recover PO matching on a large fraction of invoices with no model retraining needed.

### Priority Matrix (from actual run)

| # | Finding | Owner | Urgency | Effort |
|---|---|---|---|---|
| 1 | Enable autopilot on all queues | TAM | P1 Critical | Low |
| 2 | Fix Coupa PO line import failures | SA | P1 High | Medium |
| 3 | MDH ReadTimeout on sender match | SA | P1 High | Medium |
| 4 | Resolve supplier mismatch (30.9% of docs) | SA | P1 High | Medium |
| 5 | Fix line item amount calculation errors | SA | P2 Medium | Medium |
| 6 | Fix recipient match failures (12.1% of docs) | SA | P2 Medium | Medium |
| 7 | Tune `order_id` automation threshold | TAM | P2 Medium | Low |
| 8 | Address closed PO / PO line handling | TAM | P2 Medium | Low |
| 9 | AI training cycle for 7 core fields | TAM | P2 Medium | Medium |
| 10 | Improve document_type classification | SA/TAM | P3 Tech Debt | Medium |

**Estimated post-fix automation potential: 40–60%** on the Invoices queue (from 0%) — the skill's own projection, grounded in blocker volumes.

---

## 4. Commercial Model

### Who We Target
- Accounts **in production for ≥ 1 quarter**
- **Stable** — not in escalation, not in an active project
- Typically under-served because the SA team is occupied with new implementations

### When We Reach Out
- When Q is low on one-time revenue → generate nice-to-have service jobs
- Proactively, on a rotating account review cadence
- Triggered by a new SA joining the account (fresh eyes)

### What We Sell
| Type | Example |
|---|---|
| SA engagement | MDH tuning, formula fix, extension modernization |
| TAM engagement | Threshold tuning, autopilot enablement, training |
| ARR expansion | Additional queues, Data Storage, Structured Formats Import |

The skill can suggest an ARR angle wherever applicable (e.g., SFI rollout is a license expansion, not just a services fee).

---

## 5. Why This Wins

### For the Hackathon Judges

1. **End-to-end, not a prototype.** The skill runs today against live customer environments. LEARNINGS.md already captures real-world edge cases from actual runs — the system is learning.

2. **Self-improving.** After every client run, the SA writes back DOs and DON'Ts. The skill gets smarter without any code changes. No other team has a feedback loop baked into the tool itself.

3. **Evidence-grounded, not speculative.** Every finding references a specific queue ID, hook ID, or Data Storage collection. The commercial team can walk into a customer call with a concrete proof point, not a slide with bullets.

4. **Two outputs in one session.** Run the skill → get a Priority Matrix → approve selected items → get a complete SoW draft. What used to take an SA a day is now a 30-minute Claude session.

5. **Scales to the whole portfolio.** Any SA can run it on any account. No specialised knowledge required — the skill encodes the expertise.

### Cool Outputs to Demo

- **Priority Matrix table** with SA vs. TAM split and P1/P2/P3 urgency (generated live)
- **Auto-drafted SoW** with scoped line items, effort estimates, and ARR upsell flags
- **LEARNINGS.md** showing the skill teaching itself over successive runs (living document, version controlled)
- **Kibana evidence screenshots** tied to specific hook IDs and error types (insert actual client run logs here)

---

## 6. Slide Outline (for actual deck)

1. **Title slide** — Busman: Turn Your SA's Knowledge into Pipeline
2. **The gap** — stable accounts, silent degradation, missed revenue (1 slide)
3. **Solution overview** — the three-skill pipeline diagram (1 slide)
4. **Live demo or screen recording** — upsell skill run on a sanitised customer org
5. **Real findings** — 3–4 findings with before/after commercial impact (1 slide)
6. **Commercial model** — who, when, what we sell (1 slide)
7. **Why it wins** — self-improving, evidence-grounded, end-to-end (1 slide)
8. **Next steps** — client run logs to be inserted, ARR tracking to be added

---

## 7. Open Items Before the Presentation

- [x] Insert actual client run logs and findings — Flint Hill Resources (Org 415098) run added
- [ ] Add ARR sizing column to the Priority Matrix output
- [ ] Capture a screen recording of a full live run (sanitised org)
- [ ] Quantify: how many accounts in production for ≥ 1Q are currently unreviewed?
- [ ] Consider: can we auto-schedule a quarterly account scan as a cron trigger?
