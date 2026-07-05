"""Typed real-document dataset loading and baseline evaluation runners."""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from ..ai.event_card_service import create_event_card_from_document_payload
from ..ai.schemas import (
    ClientProfileForAI,
    CreateEventCardFromDocumentRequest,
    CreateEventCardFromDocumentResponse,
    DocumentMetadataForAI,
    FullAIAnalysisResponse,
    ImpactLevel,
)
from ..ai.service import full_ai_analysis
from ..services.document_chunker import chunk_text_for_document
from ..services.document_text_cleaner import clean_eval_metadata


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
REAL_SAMPLES_ROOT = REPOSITORY_ROOT / "data" / "real_samples"
REAL_SAMPLES_TEXT_DIR = REAL_SAMPLES_ROOT / "txt"
REAL_SAMPLES_MANIFEST = REAL_SAMPLES_ROOT / "manifest.json"
REAL_SAMPLES_CLIENTS = REAL_SAMPLES_ROOT / "eval_clients.json"


class RealSampleManifestItem(BaseModel):
    id: str
    filename: str
    enabled: bool = True
    tier: str | None = None
    source: str | None = None
    source_url: str | None = None
    document_title: str | None = None
    document_date: str | None = None
    document_type_expected: str | None = None
    domain_expected: str | None = None
    topics_expected: list[str] = Field(default_factory=list)
    impact_level_expected: ImpactLevel | None = None
    impact_levels_allowed: list[ImpactLevel] = Field(default_factory=list)
    relevant_client_tags: list[str] = Field(default_factory=list)
    non_relevant_client_tags: list[str] = Field(default_factory=list)
    notification_expected: Literal[
        "none",
        "only_relevant_clients",
        "seed_allowed",
    ] = "only_relevant_clients"
    review_state_expected: str | None = "needs_review"
    evidence_must_include: list[str] = Field(default_factory=list)
    notes: str | None = None


def load_real_samples_manifest(
    enabled_only: bool = False,
) -> list[RealSampleManifestItem]:
    """Load and validate the repository manifest. An empty list is valid."""
    raw_manifest = json.loads(REAL_SAMPLES_MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(raw_manifest, list):
        raise ValueError("Real samples manifest must contain a JSON array.")
    samples = [RealSampleManifestItem.model_validate(item) for item in raw_manifest]
    return [sample for sample in samples if sample.enabled] if enabled_only else samples


def load_real_sample_text(filename: str) -> str:
    """Read one UTF-8 sample while preventing paths outside the txt directory."""
    text_root = REAL_SAMPLES_TEXT_DIR.resolve()
    sample_path = (text_root / filename).resolve()
    if sample_path.parent != text_root:
        raise ValueError("Real sample filename must point directly into txt/.")
    if sample_path.suffix.casefold() != ".txt":
        raise ValueError("Real evaluation samples must use the .txt extension.")
    text = sample_path.read_text(encoding="utf-8").strip()
    # Dataset annotations are transport metadata, not source-document content.
    text = clean_eval_metadata(text)
    if not text:
        raise ValueError(f"Real sample is empty: {filename}")
    return text


def build_eval_client_profiles() -> list[ClientProfileForAI]:
    """Load the single manifest-aligned portfolio used by every real-doc eval."""
    raw_profiles = json.loads(REAL_SAMPLES_CLIENTS.read_text(encoding="utf-8"))
    if not isinstance(raw_profiles, list):
        raise ValueError("eval_clients.json must contain a JSON array.")
    return [ClientProfileForAI.model_validate(profile) for profile in raw_profiles]


def run_full_analysis_for_sample(
    sample: RealSampleManifestItem,
) -> FullAIAnalysisResponse:
    """Run the production full-analysis service against the eval portfolio."""
    return full_ai_analysis(
        load_real_sample_text(sample.filename),
        build_eval_client_profiles(),
    )


def run_upload_card_like_flow_for_sample(
    sample: RealSampleManifestItem,
) -> CreateEventCardFromDocumentResponse:
    """Run extraction's downstream chunk/card flow without HTTP multipart."""
    text = load_real_sample_text(sample.filename)
    return create_event_card_from_document_payload(
        CreateEventCardFromDocumentRequest(
            document_id=sample.id,
            version_id="eval-v1",
            chunks=chunk_text_for_document(text),
            metadata=DocumentMetadataForAI(
                title=sample.document_title,
                source=sample.source,
                original_url=sample.source_url,
                publication_date=sample.document_date,
            ),
            source_type="real_sample",
            source_url=sample.source_url,
            client_profiles=build_eval_client_profiles(),
        )
    )
