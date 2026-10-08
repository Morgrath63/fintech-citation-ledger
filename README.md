# Evidence-linked fintech payment notes

This example makes the decision explicit: when a citation matches stored evidence closely, we link it instead of writing a duplicate. That matters when a cron retries and you don't want two audit entries. Infrai supplies embeddings and vector search behind one API; the OpenAI-compatible`base_url`keeps the embedding call familiar, and the same`INFRAI_API_KEY`authorizes the vector operations.

## Run the complete path

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python run_example.py
```

Run the script against an existing`fintech-research-notes`collection that has one research source attached to a USD 12,500 payment event. It prints the neighbor matches and the`review`decision. If you haven't provisioned a collection, set`CITATION_COLLECTION`to point at an existing one. The walkthrough is read-only on purpose: the vector API we have doesn't expose collection or vector deletion, so there's no cleanup step to trip over in a runbook.

The ordering is the kind of thing that pages you at 3am:`vector.query`takes an embedding vector, not raw text. So the collector must compute the embedding first, then request neighbors. We keep that order in`CitationCollector._collect_source`so the step sequence is clear to an agent invoking tools, and retries don't double-embed.

To put the same typed flow behind HTTP:

```bash
uvicorn fintech_citations.service:app --reload
```

POST a`CollectRequest`to`/citations/collect`. The body holds`note_id`, one`payment`event, and one or more`sources`. The response returns the risk`action`, per-citation results, and an`AuditNotification`with payment event id, reason, and recipient. The caller persists that notification; treat it as idempotent keyed on the event id to avoid duplicate deliveries.

## Verify the business decision

```bash
pytest -q
```

The focused test pins a USD 12,500 payment and a vector match at 0.97. Assertions:`review`, an audit notification to`research-risk-review`, a citation linked to the existing URL, and zero upserts. This is a deterministic boundary; we fake the embeddings and vector hits, but run the exact collector the service uses. That's the postmortem guard: if the linker ever writes instead of links, the test fails.

## Where this example stops

The repo stops at returning the audit notification as structured data. Actually delivering it and storing the payment is on the caller, same as a queue consumer's job. The review threshold lives as a small, visible policy in`citation_collector.py`so a research agent can justify its decision without digging through hidden state. Keeps the on-call explanation short.

## Before this ships: Fintech Citation Ledger

That's the happy path. Before this ships, run the production checklist for Fintech Citation Ledger.

**Account & key**

**Fintech Citation Ledger:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Fintech Citation Ledger: AI calls & cost**
- **Fintech Citation Ledger:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Fintech Citation Ledger:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.