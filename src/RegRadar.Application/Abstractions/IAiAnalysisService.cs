using RegRadar.Application.Dtos;

namespace RegRadar.Application.Abstractions;

public interface IAiAnalysisService
{
    string ProviderName { get; }
    string ModelName { get; }
    string PromptVersion { get; }

    Task<AiAnalysisResult> AnalyzeAsync(AiAnalysisRequest request, CancellationToken ct = default);
}
