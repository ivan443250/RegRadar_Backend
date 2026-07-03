using RegRadar.Domain.Enums;

namespace RegRadar.Application.Dtos;

public record AiAnalysisResult(
    string Title,
    string Summary,
    ImpactLevel ImpactLevel,
    string ImpactExplanation,
    DateOnly? EffectiveDate,
    string[] Tags);
