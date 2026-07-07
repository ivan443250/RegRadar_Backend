import time

from ..constants import DEFAULT_MODEL_VERSION
from .base import LLMRequest, LLMRawResponse


class MockLLMProvider:
    """Mock-провайдер LLM для тестирования gateway.

    Возвращает валидный JSON с результатами rule-based анализа.
    Использует бизнес-логику из ai.mock_provider.analyze_document.
    """

    name = "mock"

    def complete(self, request: LLMRequest) -> LLMRawResponse:
        start = time.perf_counter()

        if request.metadata.get("task") == "rag_answer":
            from ..schemas import RagLLMOutput

            fragments = request.metadata.get("rag_fragments") or []
            audience = request.metadata.get("audience", "bank_employee")
            used_ids = [str(item["chunk_id"]) for item in fragments]
            source_text = " ".join(str(item["text"]) for item in fragments[:2])
            answer = (
                "На основании найденных фрагментов можно сделать "
                f"предварительный вывод: {source_text}"
            )
            notice = (
                "Это информационное уведомление и не является юридической консультацией."
                if audience == "client"
                else "Ответ носит информационный характер и требует проверки профильным специалистом."
            )
            output = RagLLMOutput(
                answer=answer,
                no_data=False,
                used_fragment_ids=used_ids,
                safety_notice=notice,
            )
            return LLMRawResponse(
                raw_text=output.model_dump_json(),
                model=request.model or DEFAULT_MODEL_VERSION,
                provider=self.name,
                tokens_used=len(request.prompt.split()),
                latency_ms=(time.perf_counter() - start) * 1000,
                finish_reason="stop",
                metadata=request.metadata,
            )

        # Переиспользуем существующий rule-based анализ
        from ..mock_provider import analyze_document

        # Prompt-based сервис передаёт исходный документ отдельно, чтобы mock
        # анализировал пользовательский текст, а не инструкции шаблона.
        document_text = request.metadata.get("document_text", request.prompt)
        doc = analyze_document(str(document_text))
        raw_text = doc.model_dump_json(indent=2)

        latency_ms = (time.perf_counter() - start) * 1000

        return LLMRawResponse(
            raw_text=raw_text,
            model=request.model or DEFAULT_MODEL_VERSION,
            provider=self.name,
            tokens_used=len(request.prompt.split()),
            latency_ms=latency_ms,
            finish_reason="stop",
            metadata=request.metadata or {},
        )
