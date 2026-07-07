"""Camel-case DTOs exchanged with the main RegRadar.Api backend."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class MainBackendDto(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )


class MainBackendClientProfileDto(MainBackendDto):
    id: str
    company_name: str
    okved: str | None = None
    industry: str | None = None
    size: int | str
    has_foreign_trade: bool
    uses_online_payments: bool
    handles_personal_data: bool
    cash_operations_level: int | str
    risk_profile: int | str
    bank_segment: str | None = None


class MainBackendDocumentDto(MainBackendDto):
    id: str
    source_id: str | None = None
    title: str
    original_url: str | None = None
    regulator: str | None = None
    document_type: int | str
    publication_date: str | None = None
    status: int | str
    processing_status: int | str
    created_at: str


class MainBackendDocumentForAI(MainBackendDto):
    id: str
    title: str
    text: str
    original_url: str | None = None
    regulator: str | None = None
    document_type: int | str | None = None
    publication_date: str | None = None


class MainBackendRegulatoryEventPayload(MainBackendDto):
    document_id: str
    title: str
    summary: str
    impact_level: int
    impact_explanation: str | None = None
    effective_date: str | None = None
    status: int
    tags: list[str] = Field(default_factory=list)


class MainBackendClientImpactPayload(MainBackendDto):
    regulatory_event_id: str | None = None
    client_profile_id: str
    company_name: str
    impact_level: int
    explanation: str


class MainBackendNotificationPayload(MainBackendDto):
    regulatory_event_id: str | None = None
    client_profile_id: str | None = None
    payload: str
    channel: int
    status: int


class IntegrationAnalyzeDocumentRequest(MainBackendDto):
    document: MainBackendDocumentForAI
    client_profiles: list[MainBackendClientProfileDto] | None = None
    model_override: str | None = None
    request_id: str | None = None


class IntegrationAnalyzeDocumentResponse(MainBackendDto):
    document_id: str
    regulatory_event: MainBackendRegulatoryEventPayload
    client_impacts: list[MainBackendClientImpactPayload]
    notification_drafts: list[MainBackendNotificationPayload]
    evidence: list[dict[str, Any]]
    rag_context: dict[str, Any]
    ai_metadata: dict[str, Any]
    raw_ai_result: dict[str, Any] | None = None


class MainBackendClientProfilesDebugResponse(MainBackendDto):
    main_profiles: list[MainBackendClientProfileDto]
    ai_profiles: list[dict[str, Any]]


class MainBackendIntegrationHealthResponse(MainBackendDto):
    main_backend_url: str | None = None
    main_backend_reachable: bool
    ai_service_health: dict[str, Any]
    notes: list[str] = Field(default_factory=list)


class MainBackendDocumentChunkDto(MainBackendDto):
    id: str
    chunk_index: int
    content: str
    token_count: int | None = None


# --- Minimal production contract consumed by the .NET backend at /analyze ---

class BackendContractClientDto(MainBackendDto):
    client_id: str
    company_name: str
    okved: str | None = None
    industry: str | None = None
    size: str | None = None
    has_foreign_trade: bool = False
    uses_online_payments: bool = False
    handles_personal_data: bool = False
    cash_operations_level: str | None = None
    risk_profile: str | None = None
    bank_segment: str | None = None


class BackendContractChunkDto(MainBackendDto):
    chunk_id: str
    chunk_index: int = 0
    content: str
    page_number: int | None = None
    section_title: str | None = None


class BackendContractAnalyzeRequest(MainBackendDto):
    document_id: str
    title: str
    text: str
    chunks: list[str | BackendContractChunkDto] = Field(default_factory=list)
    clients: list[BackendContractClientDto] = Field(default_factory=list)


class BackendContractKeyDate(BaseModel):
    date: str
    meaning: str


class BackendContractDocumentAnalysis(BaseModel):
    title: str
    short_summary: str
    long_summary: str | None = None
    domain: str | None = None
    regulator: str | None = None
    document_type: str | None = None
    status: str | None = None
    topics: list[str]
    affected_industries: list[str]
    affected_processes: list[str] = Field(default_factory=list)
    key_dates: list[BackendContractKeyDate] | None = None
    obligations: list[str]
    restrictions: list[str] = Field(default_factory=list)
    penalties_or_consequences: list[str] = Field(default_factory=list)
    source_fragments: list[str]
    confidence: float


class BackendContractImpact(BaseModel):
    impact_score: int
    impact_level: Literal["low", "medium", "high", "critical"]
    bank_impact: str | None = None
    client_impact: str | None = None
    affected_processes: list[str] = Field(default_factory=list)
    possible_consequences: list[str] = Field(default_factory=list)
    reasoning: str
    evidence_fragments: list[str]
    urgency: str
    confidence: float


class BackendContractClientRelevance(BaseModel):
    client_id: str
    client_name: str | None = None
    relevance_score: int
    relevance_level: Literal["low", "medium", "high", "critical"]
    matched_factors: list[str]
    explanation_for_bank: str
    explanation_for_client: str
    evidence_fragments: list[str]
    recommended_notification_type: str | None = None


class BackendContractEvidenceFragment(MainBackendDto):
    fragment_id: str
    text: str
    source_type: str
    document_id: str | None = None
    version_id: str | None = None
    chunk_id: str | None = None
    source_url: str | None = None
    evidence_role: str


class BackendContractNotificationDraft(MainBackendDto):
    notification_id: str | None = None
    client_id: str
    client_name: str
    title: str
    short_message: str
    full_message: str
    client_friendly_explanation: str
    source_link: str | None = None
    disclaimer: str
    priority: str
    channel_payload: dict = Field(default_factory=dict)
    document_id: str | None = None
    version_id: str = "v1"
    source_chunk_ids: list[str] = Field(default_factory=list)


class BackendContractReview(MainBackendDto):
    state: str
    required: bool
    no_data_reason: str | None = None


class BackendContractMetadata(MainBackendDto):
    runtime: str
    fallback_used: bool = False
    fallback_reason: str | None = None
    processing_mode: str | None = None
    client_profiles_source: str | None = None
    warnings: list[str] = Field(default_factory=list)
    selected_model: str | None = None
    request_id: str | None = None
    llm_call_ids: list[str] = Field(default_factory=list)
    latency_ms: int | None = None


class BackendContractAnalyzeResponse(MainBackendDto):
    provider: str
    model: str
    prompt_version: str
    analysis: BackendContractDocumentAnalysis
    impact: BackendContractImpact
    client_relevances: list[BackendContractClientRelevance]
    metadata: BackendContractMetadata | None = None
    review: BackendContractReview | None = None
    evidence: list[BackendContractEvidenceFragment] = Field(default_factory=list)
    notification_drafts: list[BackendContractNotificationDraft] = Field(
        default_factory=list
    )


class BackendContractHealthResponse(MainBackendDto):
    status: str
    service: str = "regradar-ai"
    provider_mode: str
    default_model: str
    prompts: list[str]
    storage: dict[str, str] = Field(default_factory=dict)
