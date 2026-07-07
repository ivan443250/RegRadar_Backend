"""Process-local demo context store for RAG-lite. Not production persistence."""

from collections import OrderedDict
from threading import RLock

from .schemas import DocumentChunkForAI, EvidenceFragment, RagFragmentInput


_MAX_CONTEXTS = 50
_contexts: OrderedDict[tuple[str, str], list[RagFragmentInput]] = OrderedDict()
_lock = RLock()


def save_document_context(
    document_id: str,
    version_id: str,
    fragments: list[RagFragmentInput],
) -> None:
    key = (document_id, version_id)
    deduplicated: list[RagFragmentInput] = []
    seen: set[tuple[str, str]] = set()
    for fragment in fragments:
        marker = (fragment.chunk_id, fragment.text)
        if marker in seen:
            continue
        seen.add(marker)
        deduplicated.append(fragment)
    with _lock:
        _contexts[key] = deduplicated
        _contexts.move_to_end(key)
        while len(_contexts) > _MAX_CONTEXTS:
            _contexts.popitem(last=False)


def get_document_context(
    document_id: str,
    version_id: str = "v1",
) -> list[RagFragmentInput]:
    with _lock:
        return list(_contexts.get((document_id, version_id), []))


def clear_document_contexts() -> None:
    with _lock:
        _contexts.clear()


def context_fragments_from_sources(
    document_id: str,
    version_id: str,
    *,
    chunks: list[DocumentChunkForAI] | None = None,
    evidence: list[EvidenceFragment] | None = None,
    text_fragments: list[str] | None = None,
) -> list[RagFragmentInput]:
    fragments = [
        RagFragmentInput(
            text=chunk.text,
            document_id=document_id,
            version_id=version_id,
            chunk_id=chunk.chunk_id,
            role="document_chunk",
        )
        for chunk in chunks or []
    ]
    fragments.extend(
        RagFragmentInput(
            text=item.text,
            document_id=document_id,
            version_id=version_id,
            chunk_id=item.chunk_id or item.fragment_id,
            role=item.evidence_role,
        )
        for item in evidence or []
    )
    fragments.extend(
        RagFragmentInput(
            text=text,
            document_id=document_id,
            version_id=version_id,
            chunk_id=f"source_{index + 1}",
            role="document_source",
        )
        for index, text in enumerate(text_fragments or [])
        if text.strip()
    )
    return fragments
