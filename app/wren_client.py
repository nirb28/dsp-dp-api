import hashlib
import json
from typing import Any

import httpx
from pydantic import AnyHttpUrl

from app.models import AskRequest, DataProductRecord


class WrenAIClient:
    def __init__(self, base_url: AnyHttpUrl) -> None:
        self.base_url = str(base_url).rstrip("/")

    async def deploy_semantics(self, record: DataProductRecord) -> dict[str, Any]:
        mdl_hash = self.mdl_hash(record)
        payload = {
            "project_id": record.project.id,
            "mdl": json.dumps(record.mdl),
            "id": mdl_hash,
            "request_from": "api",
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{self.base_url}/v1/semantics-preparations", json=payload)
        if response.status_code == 404:
            return {"status": "skipped", "reason": "semantics preparation endpoint was not found"}
        self._raise_for_status(response)
        return response.json()

    async def ask(self, record: DataProductRecord, request: AskRequest) -> dict[str, Any]:
        payload = {
            **request.extra,
            "project_id": record.project.id,
            "query": request.question,
            "mdl_hash": record.mdl_hash or self.mdl_hash(record),
            "request_from": "api",
        }
        if request.thread_id is not None:
            payload["thread_id"] = request.thread_id
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{self.base_url}/v1/asks", json=payload)
        self._raise_for_status(response)
        return response.json()

    async def ask_result(self, query_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(f"{self.base_url}/v1/asks/{query_id}/result")
        self._raise_for_status(response)
        return response.json()

    async def ask_streaming_result(self, query_id: str):
        client = httpx.AsyncClient(timeout=None)
        request = client.build_request("GET", f"{self.base_url}/v1/asks/{query_id}/streaming-result")
        response = await client.send(request, stream=True)
        try:
            self._raise_for_status(response)
            async for chunk in response.aiter_bytes():
                yield chunk
        finally:
            await response.aclose()
            await client.aclose()

    def mdl_hash(self, record: DataProductRecord) -> str:
        mdl = json.dumps(record.mdl)
        return hashlib.sha256(f"{record.project.id}:{mdl}".encode("utf-8")).hexdigest()

    def _raise_for_status(self, response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise httpx.HTTPStatusError(
                f"{exc} Response body: {response.text}",
                request=exc.request,
                response=exc.response,
            ) from exc
