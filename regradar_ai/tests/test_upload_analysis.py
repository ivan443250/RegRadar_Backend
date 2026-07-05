"""Tests for TXT/PDF upload analysis through the existing AI pipeline."""

import json

from app.ai.schemas import FullAIAnalysisResponse
from app.services.document_text_extractor import MAX_FILE_SIZE_BYTES


SAMPLE_TEXT = (
    "Проект предусматривает новые требования к обработке персональных данных. "
    "Организации должны соблюдать положения 152-ФЗ и хранить согласия клиентов."
)


def _minimal_pdf(text: str | None) -> bytes:
    """Build a tiny pypdf-compatible PDF with an optional text-layer string."""
    stream = (
        f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("ascii")
        if text is not None
        else b""
    )
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(stream)).encode("ascii")
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode("ascii"))
        pdf.extend(body)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)


def test_upload_txt_returns_typed_full_analysis(client):
    content = SAMPLE_TEXT.encode("utf-8")
    response = client.post(
        "/api/documents/upload-analysis",
        files={"file": ("152fz.txt", content, "text/plain")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "152fz.txt"
    assert data["content_type"] == "text/plain"
    assert data["extracted_text_length"] == len(SAMPLE_TEXT)
    FullAIAnalysisResponse.model_validate(data["analysis_result"])


def test_upload_txt_without_profiles_uses_seed_fallback(client):
    response = client.post(
        "/api/documents/upload-analysis",
        files={"file": ("document.txt", SAMPLE_TEXT.encode(), "text/plain")},
    )

    result = response.json()["analysis_result"]
    assert result["analysis_metadata"]["client_profiles_source"] == "seed_fallback"
    assert any(item["client_id"].startswith("seed-") for item in result["client_relevance"])


def test_upload_txt_custom_profiles_control_matching(client):
    profiles = [
        {
            "client_id": "upload-custom-pd",
            "company_name": "ООО Upload Клиент",
            "handles_personal_data": True,
        }
    ]
    response = client.post(
        "/api/documents/upload-analysis",
        files={"file": ("document.txt", SAMPLE_TEXT.encode(), "text/plain")},
        data={"client_profiles_json": json.dumps(profiles, ensure_ascii=False)},
    )

    assert response.status_code == 200
    result = response.json()["analysis_result"]
    assert result["analysis_metadata"]["client_profiles_source"] == "request"
    assert [item["client_id"] for item in result["client_relevance"]] == [
        "upload-custom-pd"
    ]


def test_upload_empty_txt_returns_422(client):
    response = client.post(
        "/api/documents/upload-analysis",
        files={"file": ("empty.txt", b"", "text/plain")},
    )

    assert response.status_code == 422
    assert "empty" in response.json()["detail"].lower()


def test_upload_non_utf8_txt_returns_400(client):
    response = client.post(
        "/api/documents/upload-analysis",
        files={"file": ("legacy.txt", b"\xff\xfe\xfd", "text/plain")},
    )

    assert response.status_code == 400
    assert "utf-8" in response.json()["detail"].lower()


def test_upload_invalid_client_profiles_json_returns_422(client):
    response = client.post(
        "/api/documents/upload-analysis",
        files={"file": ("document.txt", SAMPLE_TEXT.encode(), "text/plain")},
        data={"client_profiles_json": "{not-json"},
    )

    assert response.status_code == 422
    assert "client_profiles_json" in response.json()["detail"]


def test_upload_invalid_client_profile_schema_returns_422(client):
    response = client.post(
        "/api/documents/upload-analysis",
        files={"file": ("document.txt", SAMPLE_TEXT.encode(), "text/plain")},
        data={"client_profiles_json": '[{"company_name": "No ID"}]'},
    )

    assert response.status_code == 422
    assert "client_profiles_json" in response.json()["detail"]


def test_upload_unsupported_extension_returns_400(client):
    response = client.post(
        "/api/documents/upload-analysis",
        files={"file": ("document.docx", b"not a docx", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert "only .txt and .pdf" in response.json()["detail"].lower()


def test_upload_over_size_limit_returns_413(client):
    response = client.post(
        "/api/documents/upload-analysis",
        files={
            "file": (
                "large.txt",
                b"a" * (MAX_FILE_SIZE_BYTES + 1),
                "text/plain",
            )
        },
    )

    assert response.status_code == 413
    assert "10 mb" in response.json()["detail"].lower()


def test_upload_pdf_with_text_layer_runs_analysis(client):
    response = client.post(
        "/api/documents/upload-analysis",
        files={"file": ("document.pdf", _minimal_pdf("152-FZ requirements"), "application/pdf")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "document.pdf"
    assert data["extracted_text_length"] == len("152-FZ requirements")
    FullAIAnalysisResponse.model_validate(data["analysis_result"])


def test_upload_pdf_without_text_returns_clear_422(client):
    response = client.post(
        "/api/documents/upload-analysis",
        files={"file": ("scan.pdf", _minimal_pdf(None), "application/pdf")},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "does not contain extractable text" in detail
    assert "OCR is not supported" in detail


def test_upload_pdf_without_signature_returns_400(client):
    response = client.post(
        "/api/documents/upload-analysis",
        files={"file": ("fake.pdf", b"not really a PDF", "application/pdf")},
    )

    assert response.status_code == 400
    assert "%PDF signature" in response.json()["detail"]


def test_upload_endpoint_is_present_in_openapi(client):
    schema = client.get("/openapi.json").json()
    assert "/api/documents/upload-analysis" in schema["paths"]
