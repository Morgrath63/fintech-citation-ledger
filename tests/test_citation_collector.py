from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fintech_citations.citation_collector import CitationCollector
from fintech_citations.models import CollectRequest, PaymentEvent, ResearchSource, RiskAction


class RecordingClient:
    def __init__(self) -> None:
        self.upserts: list[dict[str, object]] = []

    def embed(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]

    def query(self, collection: str, embedding: list[float]) -> dict[str, object]:
        return {
            "matches": [
                {
                    "id": "existing-citation",
                    "score": 0.97,
                    "metadata": {"url": "https://bank.example/research/rail-risk"},
                }
            ]
        }

    def upsert(
        self,
        collection: str,
        vectors: list[dict[str, object]],
        *,
        idempotency_key: str,
    ) -> dict[str, object]:
        self.upserts.append({"vectors": vectors, "key": idempotency_key})
        return {}


def test_high_value_payment_marks_duplicate_and_emits_review_notification() -> None:
    client = RecordingClient()
    collector = CitationCollector(client, "fintech-notes")
    request = CollectRequest(
        note_id="note-42",
        payment=PaymentEvent(
            event_id="payment-42",
            amount=Decimal("12500"),
            currency="USD",
            counterparty="Clearing Partner",
            occurred_at=datetime(2026, 9, 5, tzinfo=timezone.utc),
        ),
        sources=[
            ResearchSource(
                title="Rail settlement exposure",
                url="https://bank.example/research/rail-exposure",
                excerpt="Settlement windows determine intraday exposure.",
            )
        ],
    )

    result = collector.collect(request)

    assert result.action is RiskAction.REVIEW
    assert result.notification.event_id == "payment-42"
    assert result.notification.recipient == "research-risk-review"
    assert result.citations[0].stored is False
    assert result.citations[0].duplicate_of == "https://bank.example/research/rail-risk"
    assert client.upserts == []
