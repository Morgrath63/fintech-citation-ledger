"""Query an existing collection for one fintech research-note example."""

from __future__ import annotations

import json
import os

from fintech_citations.citation_collector import decide_risk
from fintech_citations.infrai_client import InfraiClient
from fintech_citations.models import CollectRequest


def main() -> None:
    request = CollectRequest.model_validate(
        {
            "note_id": "note-payment-rail-17",
            "payment": {
                "event_id": "pay-2026-0905-001",
                "amount": "12500.00",
                "currency": "USD",
                "counterparty": "Example Clearing Bank",
                "occurred_at": "2026-09-05T09:30:00Z",
            },
            "sources": [
                {
                    "title": "Payment rail settlement note",
                    "url": "https://example.com/research/settlement",
                    "excerpt": "Settlement timing changes the operational exposure window.",
                }
            ],
        }
    )
    collection = os.environ.get("CITATION_COLLECTION", "fintech-research-notes")
    client = InfraiClient()
    try:
        source = request.sources[0]
        citation_text = f"{source.title}\n{source.url}\n{source.excerpt}"
        embedding = client.embed(citation_text)
        matches = client.query(collection, embedding).get("matches") or []
        action, reason = decide_risk(request.payment)
        print(
            json.dumps(
                {
                    "note_id": request.note_id,
                    "action": action.value,
                    "reason": reason,
                    "matches": matches,
                },
                indent=2,
            )
        )
    finally:
        client.close()


if __name__ == "__main__":
    main()
