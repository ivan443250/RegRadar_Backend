"""Final /health contract used by container orchestration."""

from app.ai.gateway.config import reset_config
from app.ai.service_factory import reset_reg_radar_ai_service_for_tests


def test_health_contract_is_ready_without_paid_llm_call(client, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("/health must not call an LLM provider")

    monkeypatch.setattr(
        "app.ai.gateway.polza_provider.PolzaAIProvider.complete",
        forbidden,
    )
    reset_config()
    reset_reg_radar_ai_service_for_tests()
    response = client.get("/health")
    data = response.json()
    assert response.status_code == 200
    assert data["status"] in {"ok", "degraded"}
    assert data["service"] == "regradar-ai"
    assert data["providerMode"]
    assert data["defaultModel"]
    assert set(data["prompts"]) == {"document_analysis_v1", "rag_answer_v1"}
    assert set(data["storage"]) == {
        "documents",
        "chunks",
        "events",
        "rag_chats",
        "notifications",
    }
