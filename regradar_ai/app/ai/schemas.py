from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, computed_field


ImpactLevel = Literal["low", "medium", "high", "critical"]
UrgencyLevel = Literal["low", "medium", "high", "critical"]
RelevanceLevel = Literal["low", "medium", "high"]
PriorityLevel = Literal["low", "medium", "high", "critical"]
ReviewState = Literal["draft", "needs_review", "approved", "rejected"]
ClientProfilesSource = Literal["request", "seed_fallback"]
NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


# --- DocumentAnalysis ---

class DocumentAnalysis(BaseModel):
    title: str
    short_summary: str
    long_summary: str | None = None
    domain: str | None = None
    regulator: str | None = None
    document_type: str | None = None
    status: str | None = None
    topics: list[str] = Field(default_factory=list)
    affected_industries: list[str] = Field(default_factory=list)
    affected_processes: list[str] = Field(default_factory=list)
    key_dates: list[str] = Field(default_factory=list)
    obligations: list[str] = Field(default_factory=list)
    restrictions: list[str] = Field(default_factory=list)
    penalties_or_consequences: list[str] = Field(default_factory=list)
    source_fragments: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


# --- ImpactAssessment ---

class ImpactAssessment(BaseModel):
    impact_score: int = Field(ge=0, le=100)
    impact_level: ImpactLevel
    bank_impact: str
    client_impact: str
    urgency: UrgencyLevel
    affected_processes: list[str] = Field(default_factory=list)
    possible_consequences: list[str] = Field(default_factory=list)
    reasoning: str
    evidence_fragments: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


# --- ClientRelevance ---

class ClientRelevance(BaseModel):
    client_id: str
    client_name: str
    relevance_score: int = Field(ge=0, le=100)
    relevance_level: RelevanceLevel
    matched_factors: list[str] = Field(default_factory=list)
    explanation_for_bank: str
    explanation_for_client: str
    evidence_fragments: list[str] = Field(default_factory=list)
    recommended_notification_type: str


# --- NotificationDraft ---

class NotificationDraft(BaseModel):
    notification_id: str | None = None
    client_id: str
    client_name: str
    title: str
    short_message: str
    full_message: str
    client_friendly_explanation: str
    source_link: str | None = None
    disclaimer: str
    priority: PriorityLevel
    channel_payload: dict = Field(default_factory=dict)
    document_id: str | None = None
    version_id: str = "v1"
    source_chunk_ids: list[str] = Field(default_factory=list)


NotificationMockChannel = Literal[
    "mock",
    "email_mock",
    "bank_app_mock",
    "webhook_mock",
]


class NotificationMockSendRequest(BaseModel):
    notification_id: str | None = None
    document_id: str
    version_id: str = "v1"
    event_id: str | None = None
    client_id: str = Field(min_length=1)
    client_name: str | None = None
    channel: NotificationMockChannel = "mock"
    notification: NotificationDraft
    source_chunk_ids: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class NotificationMockSendResponse(BaseModel):
    delivery_id: str
    notification_id: str
    status: Literal["sent_mock"] = "sent_mock"
    channel: NotificationMockChannel
    sent_at: str
    client_id: str
    client_name: str | None = None
    document_id: str
    version_id: str
    saved: bool
    disclaimer: str
    metadata: dict = Field(default_factory=dict)


# --- FullAIAnalysis ---

class ClientProfileForAI(BaseModel):
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
    tags: list[str] = Field(default_factory=list)


class FullAIAnalysisRequest(BaseModel):
    text: NonEmptyText
    client_profiles: list[ClientProfileForAI] | None = None
    model_override: str | None = None
    request_id: str | None = None


class AnalysisMetadata(BaseModel):
    analysis_provider: str
    model_version: str
    prompt_version: str
    fallback_used: bool = False
    fallback_reason: str | None = None
    processing_mode: str
    client_profiles_source: ClientProfilesSource = "seed_fallback"
    warnings: list[str] = Field(default_factory=list)
    selected_model: str | None = None
    context_document_id: str | None = None
    context_version_id: str | None = None
    request_id: str | None = None
    llm_call_ids: list[str] = Field(default_factory=list)
    latency_ms: int | None = Field(default=None, ge=0)
    document_saved: bool = False
    chunks_saved: int = Field(default=0, ge=0)
    event_saved: bool = False
    rag_chat_saved: bool = False
    notification_saved: bool = False
    storage_source: str = "jsonl"

    @computed_field
    @property
    def provider(self) -> str:
        """Stable alias while preserving the existing analysis_provider API."""
        return self.analysis_provider

    @computed_field
    @property
    def runtime(self) -> str:
        if self.fallback_used:
            return "FALLBACK"
        if self.analysis_provider == "polza":
            return "POLZA"
        if self.analysis_provider == "none":
            return "NO_DATA"
        return "MOCK"


class FullAIAnalysisResponse(BaseModel):
    document_analysis: DocumentAnalysis
    impact_assessment: ImpactAssessment
    client_relevance: list[ClientRelevance]
    notification_drafts: list[NotificationDraft]
    analysis_metadata: AnalysisMetadata


class UploadAnalysisResponse(BaseModel):
    filename: str
    content_type: str | None = None
    extracted_text_length: int = Field(ge=1)
    document_id: str | None = None
    version_id: str | None = None
    analysis_result: FullAIAnalysisResponse


# --- Regulatory Event Card ---

class EvidenceFragment(BaseModel):
    fragment_id: str
    text: NonEmptyText
    source_type: str
    document_id: str | None = None
    version_id: str | None = None
    chunk_id: str | None = None
    source_url: str | None = None
    evidence_role: str


class RegulatoryEventCard(BaseModel):
    event_id: str
    title: str
    short_summary: str
    current_status: str
    review_state: ReviewState
    topics: list[str] = Field(default_factory=list)
    affected_industries: list[str] = Field(default_factory=list)
    affected_processes: list[str] = Field(default_factory=list)
    impact_score: int = Field(ge=0, le=100)
    impact_level: ImpactLevel
    urgency: UrgencyLevel
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_fragments: list[EvidenceFragment] = Field(default_factory=list)
    source_set: list[str] = Field(default_factory=list)
    model_version: str
    prompt_version: str
    created_by: str
    review_required: bool
    no_data_reason: str | None = None
    document_analysis: DocumentAnalysis
    impact_assessment: ImpactAssessment
    client_relevance: list[ClientRelevance] = Field(default_factory=list)
    notification_drafts: list[NotificationDraft] = Field(default_factory=list)
    analysis_metadata: AnalysisMetadata


class CreateEventCardRequest(BaseModel):
    text: NonEmptyText
    source_type: str | None = "uploaded_text"
    source_url: str | None = None
    model_override: str | None = None


class CreateEventCardResponse(BaseModel):
    event_card: RegulatoryEventCard


# --- Future backend integration contract ---

class DocumentChunkForAI(BaseModel):
    chunk_id: str
    text: NonEmptyText
    order_index: int
    section_title: str | None = None
    page_number: int | None = None


class DocumentMetadataForAI(BaseModel):
    title: str | None = None
    source: str | None = None
    original_url: str | None = None
    publication_date: str | None = None
    regulator: str | None = None
    document_type: str | None = None
    status: str | None = None
    text_hash: str | None = None


class CreateEventCardFromDocumentRequest(BaseModel):
    document_id: str
    version_id: str
    chunks: list[DocumentChunkForAI]
    metadata: DocumentMetadataForAI
    source_type: str = "uploaded_text"
    source_url: str | None = None
    client_profiles: list[ClientProfileForAI] | None = None
    model_override: str | None = None
    request_id: str | None = None
    use_seed_fallback: bool = True


class CreateEventCardFromDocumentResponse(BaseModel):
    event_card: RegulatoryEventCard


class UploadCreateCardResponse(BaseModel):
    filename: str
    content_type: str | None = None
    extracted_text_length: int = Field(ge=1)
    document_id: str
    version_id: str
    chunks_count: int = Field(ge=1)
    card: CreateEventCardFromDocumentResponse


class AIModelInfo(BaseModel):
    id: str
    label: str
    description: str


class AIModelsResponse(BaseModel):
    provider: str
    default_model: str
    allowed_models: list[AIModelInfo]


# --- RAG-lite ---

RagAudience = Literal["bank_employee", "client"]


class RagFragmentInput(BaseModel):
    text: NonEmptyText
    document_id: str
    version_id: str = "v1"
    chunk_id: str
    role: str | None = None


class RagAskRequest(BaseModel):
    question: NonEmptyText
    document_id: str | None = None
    version_id: str = "v1"
    audience: RagAudience = "bank_employee"
    top_k: int = Field(default=5, ge=1, le=20)
    model_override: str | None = None
    source_fragments: list[RagFragmentInput] | None = None
    chunks: list[DocumentChunkForAI] | None = None
    request_id: str | None = None
    chat_id: str | None = None


class RagSourceFragment(BaseModel):
    text: NonEmptyText
    document_id: str
    version_id: str
    chunk_id: str
    score: float = Field(ge=0.0)
    role: str | None = None


class RagLLMOutput(BaseModel):
    answer: str
    no_data: bool = False
    used_fragment_ids: list[str] = Field(default_factory=list)
    safety_notice: str


class RagAnswer(BaseModel):
    answer: str
    audience: RagAudience
    no_data: bool
    source_fragments: list[RagSourceFragment] = Field(default_factory=list)
    safety_notice: str
    metadata: AnalysisMetadata
