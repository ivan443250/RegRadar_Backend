using RegRadar.Domain.Enums;

namespace RegRadar.Application.Dtos;

public record RegulatoryEventDto(
    Guid Id,
    Guid DocumentId,
    string Title,
    string Summary,
    ImpactLevel ImpactLevel,
    string? ImpactExplanation,
    DateOnly? EffectiveDate,
    EventStatus Status,
    List<string> Tags,
    DateTimeOffset CreatedAt,
    int? ImpactScore,
    string? Urgency,
    string? Domain,
    string? ReviewState,
    bool ReviewRequired,
    AiAnalysisDetails? AiDetails);
