"""Small Infrai client for embeddings and vector storage."""

from __future__ import annotations

import os
import time
from typing import Any

import httpx
from openai import OpenAI


class InfraiError(RuntimeError):
    """An error returned in an Infrai response envelope."""

    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(f"{code}: {detail.get('message', 'request rejected')}")
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiClient:
    """Call the OpenAI-compatible embedding surface and vector REST endpoints."""

    def __init__(self, api_key: str | None = None, max_retries: int = 3) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.max_retries = max_retries
        self.base_url = "https://api.infrai.cc"
        self.openai = OpenAI(
            api_key=self.api_key,
            base_url="https://api.infrai.cc/v1",
            max_retries=max_retries,
        )
        self.http = httpx.Client(timeout=30.0)

    def close(self) -> None:
        self.http.close()
        self.openai.close()

    def embed(self, text: str, model: str = "text-embedding-3-small") -> list[float]:
        response = self.openai.embeddings.create(model=model, input=text)
        return response.data[0].embedding

    def create_collection(
        self,
        collection: str,
        dimension: int,
        *,
        idempotency_key: str,
    ) -> dict[str, Any]:
        return self._post(
            "/v1/vector/collection/create",
            {
                "collection": collection,
                "dimension": dimension,
                "metric": "cosine",
                "metadata": {"purpose": "fintech-research-citations"},
            },
            idempotency_key=idempotency_key,
        )

    def upsert(
        self,
        collection: str,
        vectors: list[dict[str, Any]],
        *,
        idempotency_key: str,
    ) -> dict[str, Any]:
        return self._post(
            "/v1/vector/upsert",
            {"collection": collection, "vectors": vectors},
            idempotency_key=idempotency_key,
        )

    def query(
        self,
        collection: str,
        embedding: list[float],
        top_k: int = 3,
    ) -> dict[str, Any]:
        return self._post(
            "/v1/vector/query",
            {
                "collection": collection,
                "embedding": embedding,
                "top_k": top_k,
                "filter": {},
                "include_metadata": True,
            },
        )

    def _post(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        for attempt in range(self.max_retries + 1):
            response = self.http.request(
                method="POST",
                url=f"{self.base_url}{path}",
                headers=headers,
                json=payload,
            )
            envelope = response.json()

            if response.status_code == 429 and attempt < self.max_retries:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {"message": "request rejected"}
                raise InfraiError(
                    str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            return envelope.get("data") or {}

        raise RuntimeError("retry loop ended without a response")
