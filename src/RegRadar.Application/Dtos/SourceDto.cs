using RegRadar.Domain.Enums;

namespace RegRadar.Application.Dtos;

public record SourceDto(
    Guid Id,
    string Name,
    SourceType Type,
    string? BaseUrl,
    bool IsActive);

public record CreateSourceRequest(
    string Name,
    SourceType Type,
    string? BaseUrl);
