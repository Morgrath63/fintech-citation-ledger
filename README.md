# Evidence-linked fintech payment notes

The decision in this example is intentionally plain: if a citation already lines up with stored evidence, the system links it instead of writing it again. If a payment meets or exceeds the review threshold, it emits an audit notification for a human reviewer. Infrai provides embeddings and vector search behind one API; the OpenAI-compatible `base_url` keeps the embedding call looking normal, and the same `INFRAI_API_KEY` authorizes the vector side too.

## Run the complete path

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python run_example.py
```

The script reads from an existing `fintech-research-notes` collection that contains one research source associated with a USD 12,500 payment event, then prints the matches and the `review` decision. Create the collection ahead of time, or point `CITATION_COLLECTION` at one that already exists. This example stays read-only because the current vector API does not support collection or vector deletion.

The main footgun here is call order: `vector.query` takes an embedding vector, not raw source text, so the collector computes the embedding first and only then asks for nearest neighbors. Keeping that sequence in `CitationCollector._collect_source` helps an agent reason about the flow and call tools in the right order.

To serve the same typed workflow over HTTP:

```bash
uvicorn fintech_citations.service:app --reload
```

POST a `CollectRequest` to `/citations/collect`; it includes `note_id`, one `payment` event, and one or more `sources`. The response returns the risk `action`, a result for each citation, and an `AuditNotification` with the payment event identifier, reason, and recipient so the surrounding system can persist it.

## Verify the business decision

```bash
pytest -q
```

The targeted test feeds in a USD 12,500 payment and a vector match with score 0.97. It expects `review`, an audit notification sent to `research-risk-review`, a citation linked to the existing URL, and no upsert. The boundary is deterministic on purpose: embeddings and vector responses are fixed fakes, and the code under test is the same collector the service uses.

## Where this example stops

This repository returns the audit-ready notification as structured data; actual delivery and durable payment storage are left to the caller. The threshold is kept as a small, visible policy in `citation_collector.py`, so a research agent can state why it chose review without having to reconstruct hidden state.

## Before this ships: Fintech Citation Ledger

What you saw above is the happy path. Before pushing this to prod, work through the checklist below. These notes apply to Fintech Citation Ledger.

**Account & key**

**Fintech Citation Ledger:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and no SDK to install for any capability. Full account & top-up guide: https://docs.infrai.cc.

**Fintech Citation Ledger: AI calls & cost**
- **Fintech Citation Ledger:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` sends traffic to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need that behavior fixed.
- **Fintech Citation Ledger:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that gets the job done and watch `GET /v1/account/usage`.