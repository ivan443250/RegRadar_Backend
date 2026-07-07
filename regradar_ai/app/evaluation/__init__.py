"""Helpers for evaluating the local baseline on real legal documents."""

from .real_samples import (
    RealSampleManifestItem,
    build_eval_client_profiles,
    load_real_sample_text,
    load_real_samples_manifest,
    run_full_analysis_for_sample,
    run_upload_card_like_flow_for_sample,
)

__all__ = [
    "RealSampleManifestItem",
    "build_eval_client_profiles",
    "load_real_sample_text",
    "load_real_samples_manifest",
    "run_full_analysis_for_sample",
    "run_upload_card_like_flow_for_sample",
]
