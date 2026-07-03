using RegRadar.Application.Abstractions;
using RegRadar.Application.Dtos;
using RegRadar.Domain.Enums;

namespace RegRadar.Infrastructure.Ai;

public class MockAiAnalysisService : IAiAnalysisService
{
    public string ProviderName => "mock";
    public string ModelName => "mock-v1";
    public string PromptVersion => "v1";

    public Task<AiAnalysisResult> AnalyzeAsync(string title, string text, CancellationToken ct = default)
    {
        string summary = text.Length <= 300 ? text : text[..300] + "...";

        ImpactLevel impact = text.Length switch
        {
            < 2000 => ImpactLevel.Low,
            < 10000 => ImpactLevel.Medium,
            _ => ImpactLevel.High
        };

        AiAnalysisResult result = new(
            title,
            summary,
            impact,
            $"Mock rule: impact derived from text length ({text.Length} chars).",
            null,
            ["mock", "demo"]);

        return Task.FromResult(result);
    }
}
