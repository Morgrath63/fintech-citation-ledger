"""Typed boundaries for the citation workflow."""

from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

try:
    from pydantic import BaseModel, Field, HttpUrl
except ModuleNotFoundError:  # Support source-only runtime checks.
    BaseModel = None  # type: ignore[assignment,misc]


class RiskAction(str, Enum):
    ACCEPT = "accept"
    REVIEW = "review"


if BaseModel is not None:
    class PaymentEvent(BaseModel):
        event_id: str = Field(min_length=1)
        amount: Decimal = Field(gt=0)
        currency: str = Field(pattern=r"^[A-Z]{3}$")
        counterparty: str = Field(min_length=1)
        occurred_at: datetime


    class ResearchSource(BaseModel):
        title: str = Field(min_length=1)
        url: HttpUrl
        excerpt: str = Field(min_length=1)


    class CollectRequest(BaseModel):
        note_id: str = Field(min_length=1)
        payment: PaymentEvent
        sources: list[ResearchSource] = Field(min_length=1)


    class CitationResult(BaseModel):
        source_url: str
        stored: bool
        duplicate_of: str | None = None


    class AuditNotification(BaseModel):
        event_id: str
        action: RiskAction
        reason: str
        recipient: str = "research-risk-review"


    class CollectResponse(BaseModel):
        note_id: str
        action: RiskAction
        citations: list[CitationResult]
        notification: AuditNotification
else:
    @dataclass
    class PaymentEvent:
        event_id: str
        amount: Decimal
        currency: str
        counterparty: str
        occurred_at: datetime


    @dataclass
    class ResearchSource:
        title: str
        url: str
        excerpt: str


    @dataclass
    class CollectRequest:
        note_id: str
        payment: PaymentEvent
        sources: list[ResearchSource]


    @dataclass
    class CitationResult:
        source_url: str
        stored: bool
        duplicate_of: str | None = None


    @dataclass
    class AuditNotification:
        event_id: str
        action: RiskAction
        reason: str
        recipient: str = "research-risk-review"


    @dataclass
    class CollectResponse:
        note_id: str
        action: RiskAction
        citations: list[CitationResult]
        notification: AuditNotification
