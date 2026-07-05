# Example pytest skeleton for RegRadar real samples.
# Copy/adapt into tests/test_real_samples.py after aligning imports with your project.

import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
SAMPLES_DIR = ROOT / "data" / "real_samples"


def load_manifest():
    path = SAMPLES_DIR / "manifest.json"
    if not path.exists():
        return []
    return [item for item in json.loads(path.read_text(encoding="utf-8")) if item.get("enabled", True)]


def load_clients():
    return json.loads((SAMPLES_DIR / "eval_clients.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("sample", load_manifest(), ids=lambda x: x["id"])
def test_real_sample_baseline(sample):
    # TODO: adapt imports to actual app services or TestClient endpoint.
    # text = (SAMPLES_DIR / "txt" / sample["filename"]).read_text(encoding="utf-8")
    # result = run_full_analysis(text=text, client_profiles=load_clients())
    # assert result.document_analysis.document_type == sample["document_type_expected"]
    # assert any(topic in result.document_analysis.topics for topic in sample["topics_expected"])
    # assert result.impact_assessment.impact_level == sample["impact_level_expected"]
    # assert result.event_card.review_state == sample["review_state_expected"]
    # if sample["notification_expected"] == "none":
    #     assert result.notification_drafts == []
    pass
