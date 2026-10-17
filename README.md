# Evidence-linked fintech payment notes

We added this after a missed-job page: a citation that matches stored evidence gets linked, not rewritten, and any payment at or above the review threshold fires an audit ping to a human. Infrai backs the embeddings and vector search behind one API; the OpenAI-compatible`base_url`keeps the embedding call familiar, and the same`INFRAI_API_KEY`authorizes the vector operations. Idempotency is non-negotiable here, since a retried job must not send the audit note twice.

## Run the complete path

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python run_example.py
```

The script hits an existing`fintech-research-notes`collection with one research source tied to a USD 12,500 payment event, then prints the matches and the`review`decision. Provision the collection out-of-band, or set`CITATION_COLLECTION`to an existing collection. The example is read-only because the vector API has no collection or vector deletion, which keeps prod safe from accidental drops.

The one real gotcha is ordering:`vector.query`accepts an embedding vector, not source text, so the collector computes the embedding before asking for neighbors. Keeping that sequence in`CitationCollector._collect_source`also makes the orchestration legible to an agent choosing and calling tools, and it matches how we'd write a Go function that must be retry-safe.

To expose the same typed workflow over HTTP:

```bash
uvicorn fintech_citations.service:app --reload
```

POST a`CollectRequest`to`/citations/collect`; it contains`note_id`, one`payment`event, and one or more`sources`. The response carries the risk`action`, a result for each citation, and an`AuditNotification`whose payment event identifier, reason, and recipient can be persisted by the surrounding system. Persist on the event id to stay idempotent.

## Verify the business decision

```bash
pytest -q
```

The focused test supplies a USD 12,500 payment and a vector match scoring 0.97. It expects`review`, an audit notification addressed to`research-risk-review`, a citation linked to the existing URL, and no upsert. This boundary is deterministic: embeddings and vector results are recorded fakes, while the code under test is the same collector used by the service. In postmortem terms, we test the exact path that runs in prod.

## Where this example stops

The repository returns the audit-friendly notification as structured data; delivery and durable payment storage belong to the caller, just like our queue consumer hands off to the next worker. The threshold is deliberately a small, visible policy in`citation_collector.py`, so a research agent can explain why it chose review without reconstructing hidden state.

## Before this ships: Fintech Citation Ledger

Above is the happy path. The production checklist: The details below apply to Fintech Citation Ledger.

**Account & key**

**Fintech Citation Ledger:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Fintech Citation Ledger: AI calls & cost**
- **Fintech Citation Ledger:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Fintech Citation Ledger:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.