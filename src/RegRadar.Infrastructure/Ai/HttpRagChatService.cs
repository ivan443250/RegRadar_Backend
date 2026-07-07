using System.Net.Http.Json;
using System.Text.Json.Serialization;

using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;

using RegRadar.Application.Abstractions;
using RegRadar.Application.Dtos;
using RegRadar.Infrastructure.Persistence;

namespace RegRadar.Infrastructure.Ai;

public class HttpRagChatService(
    RegRadarDbContext db,
    IHttpClientFactory httpClientFactory,
    ILogger<HttpRagChatService> logger) : IRagChatService
{
    public async Task<RagChatAnswer> AskAsync(RagChatRequest request, CancellationToken ct = default)
    {
        List<ChunkPayload> chunks = [];

        if (request.DocumentId is Guid documentId)
        {
            Guid versionId = await db.DocumentVersions
                .Where(v => v.DocumentId == documentId)
                .OrderByDescending(v => v.VersionNumber)
                .Select(v => v.Id)
                .FirstOrDefaultAsync(ct);

            if (versionId != Guid.Empty)
            {
                chunks = await db.DocumentChunks
                    .Where(c => c.DocumentVersionId == versionId)
                    .OrderBy(c => c.ChunkIndex)
                    .Select(c => new ChunkPayload(c.Id.ToString(), c.Content, c.ChunkIndex))
                    .ToListAsync(ct);
            }
        }

        string audience = request.Audience == "client" ? "client" : "bank_employee";

        AskPayload payload = new(
            request.Question,
            request.DocumentId?.ToString(),
            "v1",
            audience,
            5,
            chunks.Count > 0 ? chunks : null);

        HttpClient client = httpClientFactory.CreateClient(HttpAiAnalysisService.HttpClientName);
        using HttpResponseMessage response = await client.PostAsJsonAsync("/api/rag/ask", payload, ct);

        if (!response.IsSuccessStatusCode)
        {
            string body = await response.Content.ReadAsStringAsync(ct);
            throw new InvalidOperationException($"AI /api/rag/ask returned {(int)response.StatusCode}: {body}");
        }

        AskResponse result = await response.Content.ReadFromJsonAsync<AskResponse>(ct)
            ?? throw new InvalidOperationException("AI /api/rag/ask returned an empty body");

        logger.LogInformation("AI rag ask ok: audience={Audience} noData={NoData} sources={Sources}",
            result.Audience, result.NoData, result.SourceFragments?.Count ?? 0);

        return new RagChatAnswer(
            result.Answer ?? string.Empty,
            result.Audience ?? audience,
            result.NoData,
            result.SourceFragments?
                .Select(s => new RagChatSource(s.Text ?? string.Empty, s.DocumentId, s.VersionId, s.ChunkId, s.Score, s.Role))
                .ToList() ?? [],
            result.SafetyNotice,
            result.Metadata?.Provider,
            result.Metadata?.Runtime,
            result.Metadata?.Warnings ?? []);
    }

    private sealed record AskPayload(
        [property: JsonPropertyName("question")] string Question,
        [property: JsonPropertyName("document_id")] string? DocumentId,
        [property: JsonPropertyName("version_id")] string VersionId,
        [property: JsonPropertyName("audience")] string Audience,
        [property: JsonPropertyName("top_k")] int TopK,
        [property: JsonPropertyName("chunks")] List<ChunkPayload>? Chunks);

    private sealed record ChunkPayload(
        [property: JsonPropertyName("chunk_id")] string ChunkId,
        [property: JsonPropertyName("text")] string Text,
        [property: JsonPropertyName("order_index")] int OrderIndex);

    private sealed record AskResponse(
        [property: JsonPropertyName("answer")] string? Answer,
        [property: JsonPropertyName("audience")] string? Audience,
        [property: JsonPropertyName("no_data")] bool NoData,
        [property: JsonPropertyName("source_fragments")] List<SourcePayload>? SourceFragments,
        [property: JsonPropertyName("safety_notice")] string? SafetyNotice,
        [property: JsonPropertyName("metadata")] MetadataPayload? Metadata);

    private sealed record SourcePayload(
        [property: JsonPropertyName("text")] string? Text,
        [property: JsonPropertyName("document_id")] string? DocumentId,
        [property: JsonPropertyName("version_id")] string? VersionId,
        [property: JsonPropertyName("chunk_id")] string? ChunkId,
        [property: JsonPropertyName("score")] double Score,
        [property: JsonPropertyName("role")] string? Role);

    private sealed record MetadataPayload(
        [property: JsonPropertyName("provider")] string? Provider,
        [property: JsonPropertyName("runtime")] string? Runtime,
        [property: JsonPropertyName("warnings")] List<string>? Warnings);
}
