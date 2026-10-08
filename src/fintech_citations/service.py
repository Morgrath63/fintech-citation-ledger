"""HTTP service exposing the citation workflow."""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException

from .citation_collector import CitationCollector
from .infrai_client import InfraiClient, InfraiError
from .models import CollectRequest, CollectResponse


app = FastAPI(title="Fintech citation collector")


@app.post("/citations/collect", response_model=CollectResponse)
def collect_citations(request: CollectRequest) -> CollectResponse:
    client = InfraiClient()
    collector = CitationCollector(
        client,
        os.environ.get("CITATION_COLLECTION", "fintech-research-notes"),
    )
    try:
        return collector.collect(request)
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=client_status,
            detail={"code": exc.code, "message": str(exc.detail.get("message", "request rejected"))},
        ) from exc
    finally:
        client.close()
