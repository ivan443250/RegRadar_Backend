using System.Net.Http.Json;
using System.Text.Json.Serialization;

using Microsoft.Extensions.Logging;

using RegRadar.Application.Abstractions;
using RegRadar.Application.Dtos;
using RegRadar.Domain.Enums;

namespace RegRadar.Infrastructure.Ai;

public class HttpAiAnalysisService(
    IHttpClientFactory httpClientFactory,
    ILogger<HttpAiAnalysisService> logger) : IAiAnalysisService
{
    public const string HttpClientName = "AiModule";

    private string _provider = "ai";
    private string _model = "unknown";
    private string _promptVersion = "unknown";

    public string ProviderName => _provider;
    public string ModelName => _model;
    public string PromptVersion => _promptVersion;

    public async Task<AiAnalysisResult> AnalyzeAsync(string title, string text, CancellationToken ct = default)
    {
        HttpClient client = httpClientFactory.CreateClient(HttpClientName);

        AnalyzeRequest payload = new(string.Empty, title, text, [], []);

        using HttpResponseMessage response = await client.PostAsJsonAsync("/analyze", payload, ct);

        if (!response.IsSuccessStatusCode)
        {
            string body = await response.Content.ReadAsStringAsync(ct);
            throw new InvalidOperationException($"AI /analyze returned {(int)response.StatusCode}: {body}");
        }

        AnalyzeResponse result = await response.Content.ReadFromJsonAsync<AnalyzeResponse>(ct)
            ?? throw new InvalidOperationException("AI /analyze returned an empty body");

        _provider = string.IsNullOrWhiteSpace(result.Provider) ? "ai" : result.Provider;
        _model = string.IsNullOrWhiteSpace(result.Model) ? "unknown" : result.Model;
        _promptVersion = string.IsNullOrWhiteSpace(result.PromptVersion) ? "unknown" : result.PromptVersion;

        ImpactLevel level = (result.Impact?.ImpactLevel ?? "medium").ToLowerInvariant() switch
        {
            "low" => ImpactLevel.Low,
            "high" or "critical" => ImpactLevel.High,
            _ => ImpactLevel.Medium
        };

        DateOnly? effectiveDate = null;
        KeyDate? keyDate = result.Analysis?.KeyDates?.FirstOrDefault(k => DateOnly.TryParse(k.Date, out _));
        if (keyDate is not null && DateOnly.TryParse(keyDate.Date, out DateOnly parsed))
            effectiveDate = parsed;

        logger.LogInformation("AI /analyze ok: provider={Provider} model={Model} impact={Impact}", _provider, _model, level);

        return new AiAnalysisResult(
            string.IsNullOrWhiteSpace(result.Analysis?.Title) ? title : result.Analysis!.Title!,
            result.Analysis?.ShortSummary ?? result.Analysis?.LongSummary ?? string.Empty,
            level,
            result.Impact?.Reasoning ?? string.Empty,
            effectiveDate,
            result.Analysis?.Topics?.ToArray() ?? []);
    }

    private sealed record AnalyzeRequest(
        [property: JsonPropertyName("documentId")] string DocumentId,
        [property: JsonPropertyName("title")] string Title,
        [property: JsonPropertyName("text")] string Text,
        [property: JsonPropertyName("chunks")] string[] Chunks,
        [property: JsonPropertyName("clients")] object[] Clients);

    private sealed record AnalyzeResponse(
        [property: JsonPropertyName("provider")] string? Provider,
        [property: JsonPropertyName("model")] string? Model,
        [property: JsonPropertyName("promptVersion")] string? PromptVersion,
        [property: JsonPropertyName("analysis")] AnalysisPayload? Analysis,
        [property: JsonPropertyName("impact")] ImpactPayload? Impact);

    private sealed record AnalysisPayload(
        [property: JsonPropertyName("title")] string? Title,
        [property: JsonPropertyName("short_summary")] string? ShortSummary,
        [property: JsonPropertyName("long_summary")] string? LongSummary,
        [property: JsonPropertyName("topics")] List<string>? Topics,
        [property: JsonPropertyName("key_dates")] List<KeyDate>? KeyDates);

    private sealed record KeyDate(
        [property: JsonPropertyName("date")] string? Date,
        [property: JsonPropertyName("meaning")] string? Meaning);

    private sealed record ImpactPayload(
        [property: JsonPropertyName("impact_level")] string? ImpactLevel,
        [property: JsonPropertyName("reasoning")] string? Reasoning);
}
