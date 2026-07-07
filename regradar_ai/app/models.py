from typing import Annotated

from pydantic import BaseModel, StringConstraints


NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class AnalyzeRequest(BaseModel):
    text: NonEmptyText


class RegulatoryEventResponse(BaseModel):
    title: str
    summary: str
    category: str
    impact: str
    impact_reason: str


class AffectedClientResponse(BaseModel):
    name: str
    segment: str
    match_reason: str


class NotificationResponse(BaseModel):
    client_name: str
    message: str


class AnalyzeResponse(BaseModel):
    event: RegulatoryEventResponse
    affected_clients: list[AffectedClientResponse]
    notifications: list[NotificationResponse]
