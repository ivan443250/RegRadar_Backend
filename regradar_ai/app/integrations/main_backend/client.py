"""Async HTTP adapter for the main RegRadar.Api backend."""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import TypeAdapter, ValidationError

from .schemas import (
    MainBackendClientProfileDto,
    MainBackendDocumentChunkDto,
    MainBackendDocumentDto,
)


class MainBackendApiError(RuntimeError):
    pass


class MainBackendUnavailableError(MainBackendApiError):
    pass


class MainBackendResponseError(MainBackendApiError):
    pass


class MainBackendApiClient:
    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError("main backend base_url must not be empty")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = client

    async def _request(
        self,
        method: str,
        path: str,
        *,
        allow_plain_text: bool = False,
        **kwargs,
    ) -> Any:
        try:
            if self._client is not None:
                response = await self._client.request(method, path, **kwargs)
            else:
                async with httpx.AsyncClient(
                    base_url=self.base_url,
                    timeout=self.timeout,
                ) as client:
                    response = await client.request(method, path, **kwargs)
            response.raise_for_status()
            if allow_plain_text and "application/json" not in response.headers.get(
                "content-type", ""
            ).casefold():
                return response.text
            return response.json()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:500]
            raise MainBackendResponseError(
                f"Main backend returned HTTP {exc.response.status_code}: {body}"
            ) from exc
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise MainBackendUnavailableError(
                f"Main backend is unavailable at {self.base_url}: {exc}"
            ) from exc
        except ValueError as exc:
            raise MainBackendResponseError(
                "Main backend returned a non-JSON response"
            ) from exc

    async def get_client_profiles(self) -> list[MainBackendClientProfileDto]:
        data = await self._request("GET", "/api/clientprofiles")
        try:
            return TypeAdapter(list[MainBackendClientProfileDto]).validate_python(data)
        except ValidationError as exc:
            raise MainBackendResponseError(
                f"Invalid ClientProfiles response: {exc}"
            ) from exc

    async def get_document(self, document_id: str) -> MainBackendDocumentDto:
        data = await self._request("GET", f"/api/documents/{document_id}")
        try:
            return MainBackendDocumentDto.model_validate(data)
        except ValidationError as exc:
            raise MainBackendResponseError(
                f"Invalid Document response: {exc}"
            ) from exc

    async def get_documents(self) -> list[dict[str, Any]]:
        return _list_of_objects(
            await self._request("GET", "/api/documents"),
            "Documents",
        )

    async def get_document_text(self, document_id: str) -> str:
        data = await self._request(
            "GET",
            f"/api/documents/{document_id}/text",
            allow_plain_text=True,
        )
        if isinstance(data, str):
            text = data
        elif isinstance(data, dict):
            text = data.get("text") or data.get("content") or ""
        else:
            text = ""
        if not isinstance(text, str) or not text.strip():
            raise MainBackendResponseError(
                "Main backend document text response is empty or invalid"
            )
        return text

    async def get_document_chunks(
        self,
        document_id: str,
    ) -> list[MainBackendDocumentChunkDto]:
        data = await self._request("GET", f"/api/documents/{document_id}/chunks")
        try:
            chunks = TypeAdapter(list[MainBackendDocumentChunkDto]).validate_python(data)
        except ValidationError as exc:
            raise MainBackendResponseError(
                f"Invalid DocumentChunks response: {exc}"
            ) from exc
        return sorted(chunks, key=lambda item: item.chunk_index)

    async def get_regulatory_event(self, event_id: str) -> dict[str, Any]:
        data = await self._request("GET", f"/api/regulatoryevents/{event_id}")
        if not isinstance(data, dict):
            raise MainBackendResponseError("Invalid RegulatoryEvent response")
        return data

    async def get_regulatory_events(self) -> list[dict[str, Any]]:
        return _list_of_objects(
            await self._request("GET", "/api/regulatoryevents"),
            "RegulatoryEvents",
        )

    async def get_event_impacts(self, event_id: str) -> list[dict[str, Any]]:
        data = await self._request(
            "GET",
            f"/api/regulatoryevents/{event_id}/impacts",
        )
        if not isinstance(data, list):
            raise MainBackendResponseError("Invalid ClientImpacts response")
        return data

    async def get_notifications(self) -> list[dict[str, Any]]:
        return _list_of_objects(
            await self._request("GET", "/api/notifications"),
            "Notifications",
        )

    async def send_notification(
        self,
        regulatory_event_id: str,
        client_profile_id: str,
    ) -> dict[str, Any]:
        data = await self._request(
            "POST",
            "/api/notifications/send",
            json={
                "regulatoryEventId": regulatory_event_id,
                "clientProfileId": client_profile_id,
            },
        )
        if not isinstance(data, dict):
            raise MainBackendResponseError("Invalid notification send response")
        return data

    async def check_reachable(self) -> tuple[bool, str | None]:
        try:
            await self.get_client_profiles()
            return True, None
        except MainBackendApiError as exc:
            return False, str(exc)


def _list_of_objects(data: Any, resource_name: str) -> list[dict[str, Any]]:
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise MainBackendResponseError(f"Invalid {resource_name} response")
    return data
