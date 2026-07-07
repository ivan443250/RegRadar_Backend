using RegRadar.Application.Abstractions;
using RegRadar.Application.Dtos;
using RegRadar.Domain.Enums;

namespace RegRadar.Infrastructure.Ai;

public class MockAiAnalysisService : IAiAnalysisService
{
    public string ProviderName => "mock";
    public string ModelName => "mock-v1";
    public string PromptVersion => "v1";

    private const string Disclaimer =
        "Сообщение носит информационный характер и не является юридической консультацией.";

    public Task<AiAnalysisResult> AnalyzeAsync(AiAnalysisRequest request, CancellationToken ct = default)
    {
        string text = request.Text;
        string summary = text.Length <= 300 ? text : text[..300] + "...";

        ImpactLevel impact = text.Length switch
        {
            < 2000 => ImpactLevel.Low,
            < 10000 => ImpactLevel.Medium,
            _ => ImpactLevel.High
        };

        int score = impact switch
        {
            ImpactLevel.Low => 25,
            ImpactLevel.Medium => 50,
            _ => 70
        };

        string urgency = impact switch
        {
            ImpactLevel.Low => "low",
            ImpactLevel.Medium => "medium",
            _ => "high"
        };

        string firstFragment = text.Length <= 160 ? text : text[..160] + "...";

        AiAnalysisDetails details = new()
        {
            ImpactScore = score,
            Urgency = urgency,
            Confidence = 0.85,
            Domain = "neutral_no_match",
            BankImpact = "Mock-оценка: проверьте документ вручную, влияние на процессы банка не рассчитывалось.",
            ClientImpact = "Mock-оценка: влияние на бизнес клиента не рассчитывалось.",
            PossibleConsequences = ["Нет данных о санкциях в источнике"],
            SourceFragments = string.IsNullOrWhiteSpace(firstFragment) ? [] : [firstFragment],
            Evidence = string.IsNullOrWhiteSpace(firstFragment)
                ? []
                : [new AiEvidenceFragment(
                    "mock_fragment_0",
                    firstFragment,
                    "document",
                    request.DocumentId.ToString(),
                    "v1",
                    request.Chunks.Count > 0 ? request.Chunks[0].Id.ToString() : null,
                    null,
                    "impact")],
            ClientRelevances = [.. request.Clients.Take(2).Select(c => new AiClientRelevance(
                c.Id.ToString(),
                c.CompanyName,
                50,
                "medium",
                ["mock"],
                "Mock-режим: релевантность назначена демонстрационно.",
                "Изменение может касаться вашей компании — уточните у менеджера банка.",
                [],
                "email"))],
            NotificationDrafts = [.. request.Clients.Take(2).Select(c => new AiNotificationDraft(
                null,
                c.Id.ToString(),
                c.CompanyName,
                request.Title,
                summary.Length <= 120 ? summary : summary[..120] + "...",
                summary,
                "Изменение может касаться вашей компании — уточните детали у менеджера банка.",
                null,
                Disclaimer,
                urgency,
                []))],
            Review = new AiReviewInfo("needs_review", true, null),
            Metadata = new AiAnalysisMetadata(
                "MOCK", false, null, "mock", "request", [], ModelName, null, [], 0)
        };

        AiAnalysisResult result = new(
            request.Title,
            summary,
            impact,
            $"Mock rule: impact derived from text length ({text.Length} chars).",
            null,
            ["mock", "demo"],
            details);

        return Task.FromResult(result);
    }
}
