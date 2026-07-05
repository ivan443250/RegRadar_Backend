using RegRadar.Domain.Enums;

namespace RegRadar.Application.Dtos;

public record ImpactAssessment(ImpactLevel Level, string Explanation);
