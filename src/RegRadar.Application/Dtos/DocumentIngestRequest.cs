using RegRadar.Domain.Enums;

namespace RegRadar.Application.Dtos;

public record DocumentIngestRequest(
    string FileName,
    SourceType SourceType,
    string? Title = null,
    string? OriginalUrl = null,
    string? Regulator = null,
    DateOnly? PublicationDate = null,
    DocumentType DocumentType = DocumentType.Unknown);
