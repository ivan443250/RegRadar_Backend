using Microsoft.EntityFrameworkCore;

using RegRadar.Application.Abstractions;
using RegRadar.Application.Dtos;
using RegRadar.Domain.Entities;
using RegRadar.Infrastructure.Persistence;

namespace RegRadar.Infrastructure.Ai;

public class MockRagChatService(RegRadarDbContext db) : IRagChatService
{
    private const string SafetyNotice =
        "Ответ сформирован автоматически и не является юридической консультацией.";

    public async Task<RagChatAnswer> AskAsync(RagChatRequest request, CancellationToken ct = default)
    {
        string audience = request.Audience == "client" ? "client" : "bank_employee";

        RegulatoryEvent? ev = null;
        DocumentChunk? chunk = null;

        if (request.DocumentId is Guid documentId)
        {
            ev = await db.RegulatoryEvents.AsNoTracking()
                .FirstOrDefaultAsync(e => e.DocumentId == documentId, ct);

            chunk = await db.DocumentChunks.AsNoTracking()
                .Where(c => c.DocumentVersion.DocumentId == documentId)
                .OrderBy(c => c.ChunkIndex)
                .FirstOrDefaultAsync(ct);
        }

        if (ev is null)
        {
            return new RagChatAnswer(
                "Недостаточно данных для ответа: выберите документ, по которому уже выполнен анализ.",
                audience,
                true,
                [],
                SafetyNotice,
                "mock",
                "MOCK",
                []);
        }

        string answer = audience == "client"
            ? $"Если коротко: «{ev.Title}». {ev.Summary} Точные выводы лучше проверить по фрагментам источника."
            : $"По документу «{ev.Title}»: {ev.Summary} Обоснование импакта: {ev.ImpactExplanation ?? "не рассчитано"}.";

        List<RagChatSource> sources = chunk is null
            ? []
            : [new RagChatSource(
                chunk.Content.Length <= 400 ? chunk.Content : chunk.Content[..400] + "...",
                request.DocumentId?.ToString(),
                "v1",
                chunk.Id.ToString(),
                1.0,
                "context")];

        return new RagChatAnswer(answer, audience, false, sources, SafetyNotice, "mock", "MOCK", []);
    }
}
