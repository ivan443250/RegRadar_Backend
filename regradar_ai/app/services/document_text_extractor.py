"""Text extraction and upload validation for MVP document ingestion."""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from .document_text_cleaner import clean_eval_metadata


MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
SUPPORTED_EXTENSIONS = {".txt", ".pdf"}


class DocumentExtractionError(ValueError):
    """Base error with an HTTP status suitable for the upload boundary."""

    status_code = 400


class UnsupportedFileTypeError(DocumentExtractionError):
    """The filename does not have an allowed extension."""


class FileTooLargeError(DocumentExtractionError):
    """The uploaded body exceeds the MVP limit."""

    status_code = 413


class InvalidDocumentError(DocumentExtractionError):
    """The bytes cannot be decoded or parsed as the declared file type."""


class TextNotExtractedError(DocumentExtractionError):
    """The file is valid, but contains no text usable by the pipeline."""

    status_code = 422


@dataclass(frozen=True, slots=True)
class ExtractedDocumentText:
    filename: str
    content_type: str | None
    extension: str
    text: str
    extracted_text_length: int


def extract_text_from_txt(content: bytes) -> str:
    """Decode a UTF-8 text document and reject empty content."""
    try:
        text = content.decode("utf-8-sig").strip()
    except UnicodeDecodeError as exc:
        raise InvalidDocumentError("TXT file must be encoded as UTF-8.") from exc

    if not text:
        raise TextNotExtractedError("Document is empty after text extraction.")
    return text


def extract_text_from_pdf(content: bytes) -> str:
    """Extract the PDF text layer. OCR is deliberately outside the MVP."""
    if not content.startswith(b"%PDF"):
        raise InvalidDocumentError("Invalid PDF: missing %PDF signature.")

    try:
        reader = PdfReader(BytesIO(content))
        page_texts = [page.extract_text() or "" for page in reader.pages]
    except (PyPdfError, ValueError, TypeError) as exc:
        raise InvalidDocumentError("Invalid or unreadable PDF file.") from exc

    text = "\n".join(part.strip() for part in page_texts if part.strip()).strip()
    if not text:
        raise TextNotExtractedError(
            "PDF does not contain extractable text. OCR is not supported in MVP."
        )
    return text


def extract_text_from_upload(
    filename: str,
    content_type: str | None,
    content: bytes,
) -> ExtractedDocumentText:
    """Validate an upload by size and extension, then extract its text."""
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise FileTooLargeError("File is too large. Maximum upload size is 10 MB.")

    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            "Unsupported file type. Only .txt and .pdf files are supported."
        )
    if not content:
        raise TextNotExtractedError("Uploaded document is empty.")

    text = (
        extract_text_from_txt(content)
        if extension == ".txt"
        else extract_text_from_pdf(content)
    )
    text = clean_eval_metadata(text)
    if not text:
        raise TextNotExtractedError(
            "Document is empty after removing evaluation metadata."
        )
    return ExtractedDocumentText(
        filename=filename,
        content_type=content_type,
        extension=extension,
        text=text,
        extracted_text_length=len(text),
    )
