using RegRadar.Domain.Enums;

namespace RegRadar.Application.Dtos;

public record ClientImpactDto(
    Guid Id,
    Guid RegulatoryEventId,
    Guid ClientProfileId,
    string CompanyName,
    ImpactLevel ImpactLevel,
    string? Explanation);
