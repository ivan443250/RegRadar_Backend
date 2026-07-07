using RegRadar.Domain.Enums;

namespace RegRadar.Application.Dtos;

public record AiAnalysisChunk(Guid Id, int Index, string Content);

public record AiAnalysisRequest(
    Guid DocumentId,
    string Title,
    string Text,
    IReadOnlyList<AiAnalysisChunk> Chunks,
    IReadOnlyList<ClientProfileDto> Clients);

public record AiAnalysisResult(
    string Title,
    string Summary,
    ImpactLevel ImpactLevel,
    string ImpactExplanation,
    DateOnly? EffectiveDate,
    string[] Tags,
    AiAnalysisDetails? Details = null);
