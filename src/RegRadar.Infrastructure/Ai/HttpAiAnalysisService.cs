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

    public async Task<AiAnalysisResult> AnalyzeAsync(AiAnalysisRequest request, CancellationToken ct = default)
    {
        HttpClient client = httpClientFactory.CreateClient(HttpClientName);

        AnalyzePayload payload = new(
            request.DocumentId.ToString(),
            request.Title,
            request.Text,
            [.. request.Chunks.Select(c => new ChunkPayload(c.Id.ToString(), c.Index, c.Content))],
            [.. request.Clients.Select(ToClientPayload)]);

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
            string.IsNullOrWhiteSpace(result.Analysis?.Title) ? request.Title : result.Analysis!.Title!,
            result.Analysis?.ShortSummary ?? result.Analysis?.LongSummary ?? string.Empty,
            level,
            result.Impact?.Reasoning ?? string.Empty,
            effectiveDate,
            result.Analysis?.Topics?.ToArray() ?? [],
            BuildDetails(result));
    }

    private static ClientPayload ToClientPayload(ClientProfileDto c) => new(
        c.Id.ToString(),
        c.CompanyName,
        c.Okved,
        c.Industry,
        c.Size.ToString(),
        c.HasForeignTrade,
        c.UsesOnlinePayments,
        c.HandlesPersonalData,
        c.CashOperationsLevel.ToString(),
        c.RiskProfile.ToString(),
        c.BankSegment);

    private static AiAnalysisDetails BuildDetails(AnalyzeResponse result)
    {
        AnalysisPayload? analysis = result.Analysis;
        ImpactPayload? impact = result.Impact;

        return new AiAnalysisDetails
        {
            ImpactScore = impact?.ImpactScore,
            Urgency = impact?.Urgency,
            Confidence = impact?.Confidence,
            Domain = analysis?.Domain,
            DocumentStatus = analysis?.Status,
            LongSummary = analysis?.LongSummary,
            BankImpact = impact?.BankImpact,
            ClientImpact = impact?.ClientImpact,
            Obligations = analysis?.Obligations ?? [],
            Restrictions = analysis?.Restrictions ?? [],
            PenaltiesOrConsequences = analysis?.PenaltiesOrConsequences ?? [],
            AffectedProcesses = impact?.AffectedProcesses ?? analysis?.AffectedProcesses ?? [],
            PossibleConsequences = impact?.PossibleConsequences ?? [],
            AffectedIndustries = analysis?.AffectedIndustries ?? [],
            KeyDates = analysis?.KeyDates?
                .Where(k => k.Date is not null)
                .Select(k => new AiKeyDate(k.Date!, k.Meaning ?? string.Empty))
                .ToList() ?? [],
            SourceFragments = analysis?.SourceFragments ?? [],
            Evidence = result.Evidence?
                .Select(f => new AiEvidenceFragment(
                    f.FragmentId ?? string.Empty,
                    f.Text ?? string.Empty,
                    f.SourceType ?? string.Empty,
                    f.DocumentId, f.VersionId, f.ChunkId, f.SourceUrl,
                    f.EvidenceRole ?? string.Empty))
                .ToList() ?? [],
            ClientRelevances = result.ClientRelevances?
                .Select(r => new AiClientRelevance(
                    r.ClientId ?? string.Empty,
                    r.ClientName,
                    r.RelevanceScore,
                    r.RelevanceLevel ?? "low",
                    r.MatchedFactors ?? [],
                    r.ExplanationForBank ?? string.Empty,
                    r.ExplanationForClient ?? string.Empty,
                    r.EvidenceFragments ?? [],
                    r.RecommendedNotificationType))
                .ToList() ?? [],
            NotificationDrafts = result.NotificationDrafts?
                .Select(d => new AiNotificationDraft(
                    d.NotificationId,
                    d.ClientId ?? string.Empty,
                    d.ClientName ?? string.Empty,
                    d.Title ?? string.Empty,
                    d.ShortMessage ?? string.Empty,
                    d.FullMessage ?? string.Empty,
                    d.ClientFriendlyExplanation ?? string.Empty,
                    d.SourceLink,
                    d.Disclaimer ?? string.Empty,
                    d.Priority ?? "medium",
                    d.SourceChunkIds ?? []))
                .ToList() ?? [],
            Review = result.Review is null
                ? null
                : new AiReviewInfo(result.Review.State ?? "draft", result.Review.Required, result.Review.NoDataReason),
            Metadata = result.Metadata is null
                ? null
                : new AiAnalysisMetadata(
                    result.Metadata.Runtime,
                    result.Metadata.FallbackUsed,
                    result.Metadata.FallbackReason,
                    result.Metadata.ProcessingMode,
                    result.Metadata.ClientProfilesSource,
                    result.Metadata.Warnings ?? [],
                    result.Metadata.SelectedModel,
                    result.Metadata.RequestId,
                    result.Metadata.LlmCallIds ?? [],
                    result.Metadata.LatencyMs)
        };
    }

    private sealed record AnalyzePayload(
        [property: JsonPropertyName("documentId")] string DocumentId,
        [property: JsonPropertyName("title")] string Title,
        [property: JsonPropertyName("text")] string Text,
        [property: JsonPropertyName("chunks")] List<ChunkPayload> Chunks,
        [property: JsonPropertyName("clients")] List<ClientPayload> Clients);

    private sealed record ChunkPayload(
        [property: JsonPropertyName("chunkId")] string ChunkId,
        [property: JsonPropertyName("chunkIndex")] int ChunkIndex,
        [property: JsonPropertyName("content")] string Content);

    private sealed record ClientPayload(
        [property: JsonPropertyName("clientId")] string ClientId,
        [property: JsonPropertyName("companyName")] string CompanyName,
        [property: JsonPropertyName("okved")] string? Okved,
        [property: JsonPropertyName("industry")] string? Industry,
        [property: JsonPropertyName("size")] string? Size,
        [property: JsonPropertyName("hasForeignTrade")] bool HasForeignTrade,
        [property: JsonPropertyName("usesOnlinePayments")] bool UsesOnlinePayments,
        [property: JsonPropertyName("handlesPersonalData")] bool HandlesPersonalData,
        [property: JsonPropertyName("cashOperationsLevel")] string? CashOperationsLevel,
        [property: JsonPropertyName("riskProfile")] string? RiskProfile,
        [property: JsonPropertyName("bankSegment")] string? BankSegment);

    private sealed record AnalyzeResponse(
        [property: JsonPropertyName("provider")] string? Provider,
        [property: JsonPropertyName("model")] string? Model,
        [property: JsonPropertyName("promptVersion")] string? PromptVersion,
        [property: JsonPropertyName("analysis")] AnalysisPayload? Analysis,
        [property: JsonPropertyName("impact")] ImpactPayload? Impact,
        [property: JsonPropertyName("clientRelevances")] List<RelevancePayload>? ClientRelevances,
        [property: JsonPropertyName("metadata")] MetadataPayload? Metadata,
        [property: JsonPropertyName("review")] ReviewPayload? Review,
        [property: JsonPropertyName("evidence")] List<EvidencePayload>? Evidence,
        [property: JsonPropertyName("notificationDrafts")] List<DraftPayload>? NotificationDrafts);

    private sealed record AnalysisPayload(
        [property: JsonPropertyName("title")] string? Title,
        [property: JsonPropertyName("short_summary")] string? ShortSummary,
        [property: JsonPropertyName("long_summary")] string? LongSummary,
        [property: JsonPropertyName("domain")] string? Domain,
        [property: JsonPropertyName("status")] string? Status,
        [property: JsonPropertyName("topics")] List<string>? Topics,
        [property: JsonPropertyName("affected_industries")] List<string>? AffectedIndustries,
        [property: JsonPropertyName("affected_processes")] List<string>? AffectedProcesses,
        [property: JsonPropertyName("key_dates")] List<KeyDate>? KeyDates,
        [property: JsonPropertyName("obligations")] List<string>? Obligations,
        [property: JsonPropertyName("restrictions")] List<string>? Restrictions,
        [property: JsonPropertyName("penalties_or_consequences")] List<string>? PenaltiesOrConsequences,
        [property: JsonPropertyName("source_fragments")] List<string>? SourceFragments);

    private sealed record KeyDate(
        [property: JsonPropertyName("date")] string? Date,
        [property: JsonPropertyName("meaning")] string? Meaning);

    private sealed record ImpactPayload(
        [property: JsonPropertyName("impact_score")] int? ImpactScore,
        [property: JsonPropertyName("impact_level")] string? ImpactLevel,
        [property: JsonPropertyName("bank_impact")] string? BankImpact,
        [property: JsonPropertyName("client_impact")] string? ClientImpact,
        [property: JsonPropertyName("affected_processes")] List<string>? AffectedProcesses,
        [property: JsonPropertyName("possible_consequences")] List<string>? PossibleConsequences,
        [property: JsonPropertyName("reasoning")] string? Reasoning,
        [property: JsonPropertyName("urgency")] string? Urgency,
        [property: JsonPropertyName("confidence")] double? Confidence);

    private sealed record RelevancePayload(
        [property: JsonPropertyName("client_id")] string? ClientId,
        [property: JsonPropertyName("client_name")] string? ClientName,
        [property: JsonPropertyName("relevance_score")] int RelevanceScore,
        [property: JsonPropertyName("relevance_level")] string? RelevanceLevel,
        [property: JsonPropertyName("matched_factors")] List<string>? MatchedFactors,
        [property: JsonPropertyName("explanation_for_bank")] string? ExplanationForBank,
        [property: JsonPropertyName("explanation_for_client")] string? ExplanationForClient,
        [property: JsonPropertyName("evidence_fragments")] List<string>? EvidenceFragments,
        [property: JsonPropertyName("recommended_notification_type")] string? RecommendedNotificationType);

    private sealed record MetadataPayload(
        [property: JsonPropertyName("runtime")] string? Runtime,
        [property: JsonPropertyName("fallbackUsed")] bool FallbackUsed,
        [property: JsonPropertyName("fallbackReason")] string? FallbackReason,
        [property: JsonPropertyName("processingMode")] string? ProcessingMode,
        [property: JsonPropertyName("clientProfilesSource")] string? ClientProfilesSource,
        [property: JsonPropertyName("warnings")] List<string>? Warnings,
        [property: JsonPropertyName("selectedModel")] string? SelectedModel,
        [property: JsonPropertyName("requestId")] string? RequestId,
        [property: JsonPropertyName("llmCallIds")] List<string>? LlmCallIds,
        [property: JsonPropertyName("latencyMs")] long? LatencyMs);

    private sealed record ReviewPayload(
        [property: JsonPropertyName("state")] string? State,
        [property: JsonPropertyName("required")] bool Required,
        [property: JsonPropertyName("noDataReason")] string? NoDataReason);

    private sealed record EvidencePayload(
        [property: JsonPropertyName("fragmentId")] string? FragmentId,
        [property: JsonPropertyName("text")] string? Text,
        [property: JsonPropertyName("sourceType")] string? SourceType,
        [property: JsonPropertyName("documentId")] string? DocumentId,
        [property: JsonPropertyName("versionId")] string? VersionId,
        [property: JsonPropertyName("chunkId")] string? ChunkId,
        [property: JsonPropertyName("sourceUrl")] string? SourceUrl,
        [property: JsonPropertyName("evidenceRole")] string? EvidenceRole);

    private sealed record DraftPayload(
        [property: JsonPropertyName("notificationId")] string? NotificationId,
        [property: JsonPropertyName("clientId")] string? ClientId,
        [property: JsonPropertyName("clientName")] string? ClientName,
        [property: JsonPropertyName("title")] string? Title,
        [property: JsonPropertyName("shortMessage")] string? ShortMessage,
        [property: JsonPropertyName("fullMessage")] string? FullMessage,
        [property: JsonPropertyName("clientFriendlyExplanation")] string? ClientFriendlyExplanation,
        [property: JsonPropertyName("sourceLink")] string? SourceLink,
        [property: JsonPropertyName("disclaimer")] string? Disclaimer,
        [property: JsonPropertyName("priority")] string? Priority,
        [property: JsonPropertyName("sourceChunkIds")] List<string>? SourceChunkIds);
}
