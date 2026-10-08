"""Business workflow for risk-aware citation collection."""

from __future__ import annotations

import hashlib
from decimal import Decimal
from typing import Any

from .models import (
    AuditNotification,
    CitationResult,
    CollectRequest,
    CollectResponse,
    PaymentEvent,
    ResearchSource,
    RiskAction,
)


REVIEW_THRESHOLD = Decimal("10000")
DUPLICATE_SCORE = 0.92


def decide_risk(payment: PaymentEvent) -> tuple[RiskAction, str]:
    if payment.amount >= REVIEW_THRESHOLD:
        return RiskAction.REVIEW, "payment amount meets the manual-review threshold"
    return RiskAction.ACCEPT, "payment amount is below the manual-review threshold"


class CitationCollector:
    def __init__(self, client: Any, collection: str) -> None:
        self.client = client
        self.collection = collection

    def prepare_collection(self, sample_text: str) -> int:
        embedding = self.client.embed(sample_text)
        key = f"collection:{self.collection}:{len(embedding)}"
        self.client.create_collection(
            self.collection,
            len(embedding),
            idempotency_key=key,
        )
        return len(embedding)

    def collect(self, request: CollectRequest) -> CollectResponse:
        action, reason = decide_risk(request.payment)
        citations = [self._collect_source(request.note_id, source) for source in request.sources]
        notification = AuditNotification(
            event_id=request.payment.event_id,
            action=action,
            reason=reason,
        )
        return CollectResponse(
            note_id=request.note_id,
            action=action,
            citations=citations,
            notification=notification,
        )

    def _collect_source(self, note_id: str, source: ResearchSource) -> CitationResult:
        canonical_url = str(source.url)
        citation_text = f"{source.title}\n{canonical_url}\n{source.excerpt}"
        embedding = self.client.embed(citation_text)
        query_data = self.client.query(self.collection, embedding)
        duplicate = self._best_duplicate(query_data)
        if duplicate:
            return CitationResult(
                source_url=canonical_url,
                stored=False,
                duplicate_of=duplicate,
            )

        vector_id = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()
        self.client.upsert(
            self.collection,
            [
                {
                    "id": vector_id,
                    "values": embedding,
                    "metadata": {
                        "note_id": note_id,
                        "title": source.title,
                        "url": canonical_url,
                    },
                }
            ],
            idempotency_key=f"citation:{vector_id}",
        )
        return CitationResult(source_url=canonical_url, stored=True)

    @staticmethod
    def _best_duplicate(query_data: dict[str, Any]) -> str | None:
        matches = query_data.get("matches") or []
        if not matches:
            return None
        best = matches[0]
        if float(best.get("score", 0.0)) < DUPLICATE_SCORE:
            return None
        metadata = best.get("metadata") or {}
        return str(metadata.get("url") or best.get("id"))
