using RegRadar.Domain.Enums;

namespace RegRadar.Application.Dtos;

public record DocumentDto(
    Guid Id,
    Guid SourceId,
    string Title,
    string? OriginalUrl,
    string? Regulator,
    DocumentType DocumentType,
    DateOnly? PublicationDate,
    DocumentStatus Status,
    ProcessingStatus ProcessingStatus,
    DateTimeOffset CreatedAt);
