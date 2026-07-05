using System.Diagnostics;
using System.Text.Json;

using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

using RegRadar.Application.Abstractions;
using RegRadar.Application.Dtos;
using RegRadar.Domain.Entities;
using RegRadar.Domain.Enums;
using RegRadar.Infrastructure.Persistence;

namespace RegRadar.Infrastructure.Processing;

public class DocumentProcessingService(
    RegRadarDbContext db,
    IEnumerable<ITextExtractor> extractors,
    ITextNormalizer normalizer,
    ITextHasher hasher,
    ITextChunker chunker,
    IAiAnalysisService ai,
    IImpactService impactService,
    IOptions<StorageOptions> storageOptions,
    ILogger<DocumentProcessingService> logger) : IDocumentProcessingService
{
    private readonly StorageOptions _storage = storageOptions.Value;

    public async Task<DocumentUploadResult> IngestAsync(DocumentIngestRequest request, Stream content, CancellationToken ct = default)
    {
        string extension = Path.GetExtension(request.FileName);
        ITextExtractor? extractor = extractors.FirstOrDefault(e => e.CanHandle(extension));

        if (extractor is null)
            return DocumentUploadResult.UnsupportedFormat(extension);

        ProcessingJob job = new()
        {
            Type = JobType.Ingestion,
            Status = JobStatus.Running,
            Attempts = 1,
            StartedAt = DateTimeOffset.UtcNow
        };
        db.ProcessingJobs.Add(job);
        await db.SaveChangesAsync(ct);

        try
        {
            string rawFilePath = await SaveRawFileAsync(content, extension, ct);

            string rawText;
            await using (FileStream saved = File.OpenRead(rawFilePath))
            {
                rawText = await extractor.ExtractAsync(saved, ct);
            }

            string normalized = normalizer.Normalize(rawText);
            string hash = hasher.GetHash(normalized);

            Document? existing = await db.Documents.FirstOrDefaultAsync(d => d.TextHash == hash, ct);
            if (existing is not null)
            {
                File.Delete(rawFilePath);
                await CompleteJobAsync(job, existing.Id, ct);
                return DocumentUploadResult.Duplicate(existing.Id);
            }

            Source source = await GetOrCreateSourceAsync(request.SourceType, ct);

            Document document = new()
            {
                Source = source,
                Title = request.Title ?? Path.GetFileNameWithoutExtension(request.FileName),
                OriginalUrl = request.OriginalUrl,
                Regulator = request.Regulator,
                PublicationDate = request.PublicationDate,
                DocumentType = request.DocumentType,
                ProcessingStatus = ProcessingStatus.AwaitingAi,
                RawFilePath = rawFilePath,
                TextHash = hash
            };

            DocumentVersion version = new()
            {
                VersionNumber = 1,
                Text = normalized,
                TextHash = hash
            };

            IReadOnlyList<string> chunks = chunker.SliceToChunks(normalized);
            for (int i = 0; i < chunks.Count; i++)
            {
                version.Chunks.Add(new DocumentChunk
                {
                    ChunkIndex = i,
                    Content = chunks[i],
                    TokenCount = chunks[i].Length
                });
            }

            document.Versions.Add(version);
            db.Documents.Add(document);
            db.AuditLogs.Add(new AuditLog
            {
                Action = "DocumentIngested",
                EntityName = nameof(Document),
                EntityId = document.Id,
                Actor = request.SourceType.ToString(),
                Details = document.Title
            });
            await db.SaveChangesAsync(ct);

            await CompleteJobAsync(job, document.Id, ct);

            logger.LogInformation("Document {DocumentId} processed from {FileName}: {ChunkCount} chunks", document.Id, request.FileName, chunks.Count);

            await RunAiAnalysisAsync(document, normalized, ct);

            return DocumentUploadResult.Created(document.Id);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Document processing failed for {FileName}", request.FileName);

            db.ChangeTracker.Clear();
            job.Status = JobStatus.Failed;
            job.ErrorMessage = ex.Message;
            job.FinishedAt = DateTimeOffset.UtcNow;
            db.ProcessingJobs.Update(job);
            await db.SaveChangesAsync(CancellationToken.None);

            return DocumentUploadResult.Failed(ex.Message);
        }
    }

    private async Task<string> SaveRawFileAsync(Stream content, string extension, CancellationToken ct)
    {
        Directory.CreateDirectory(_storage.RawFilesPath);
        string path = Path.Combine(_storage.RawFilesPath, $"{Guid.NewGuid():N}{extension}");

        await using FileStream target = File.Create(path);
        await content.CopyToAsync(target, ct);

        return path;
    }

    private static readonly Dictionary<SourceType, (string Name, string? BaseUrl)> SourceCatalog = new()
    {
        [SourceType.UserUpload] = ("User Upload", null),
        [SourceType.BankOfRussia] = ("Банк России", "https://www.cbr.ru"),
        [SourceType.RegulationGov] = ("regulation.gov.ru", "https://regulation.gov.ru"),
        [SourceType.PravoGov] = ("pravo.gov.ru", "http://pravo.gov.ru")
    };

    private async Task<Source> GetOrCreateSourceAsync(SourceType type, CancellationToken ct)
    {
        Source? source = await db.Sources.FirstOrDefaultAsync(s => s.Type == type, ct);

        if (source is not null)
            return source;

        (string name, string? baseUrl) = SourceCatalog[type];

        source = new Source
        {
            Name = name,
            Type = type,
            BaseUrl = baseUrl
        };
        db.Sources.Add(source);

        return source;
    }

    private async Task CompleteJobAsync(ProcessingJob job, Guid documentId, CancellationToken ct)
    {
        job.DocumentId = documentId;
        job.Status = JobStatus.Succeeded;
        job.FinishedAt = DateTimeOffset.UtcNow;
        await db.SaveChangesAsync(ct);
    }

    public async Task<DocumentUploadResult> ReprocessAsync(Guid documentId, CancellationToken ct = default)
    {
        Document? document = await db.Documents.FirstOrDefaultAsync(d => d.Id == documentId, ct);

        if (document is null)
            return DocumentUploadResult.Failed("Document not found.");

        bool hasEvent = await db.RegulatoryEvents.AnyAsync(e => e.DocumentId == documentId, ct);
        if (hasEvent)
            return DocumentUploadResult.Duplicate(documentId);

        string? text = await db.DocumentVersions
            .Where(v => v.DocumentId == documentId)
            .OrderByDescending(v => v.VersionNumber)
            .Select(v => v.Text)
            .FirstOrDefaultAsync(ct);

        if (text is null)
            return DocumentUploadResult.Failed("Document has no extracted version.");

        db.AuditLogs.Add(new AuditLog
        {
            Action = "DocumentReprocessRequested",
            EntityName = nameof(Document),
            EntityId = documentId,
            Actor = "api"
        });
        await db.SaveChangesAsync(ct);

        await RunAiAnalysisAsync(document, text, ct);

        return document.ProcessingStatus == ProcessingStatus.Completed
            ? DocumentUploadResult.Created(documentId)
            : DocumentUploadResult.Failed("AI processing failed, see processing jobs.");
    }

    private async Task RunAiAnalysisAsync(Document document, string text, CancellationToken ct)
    {
        int attempts = await db.ProcessingJobs
            .CountAsync(j => j.DocumentId == document.Id && j.Type == JobType.AiProcessing, ct) + 1;

        ProcessingJob job = new()
        {
            DocumentId = document.Id,
            Type = JobType.AiProcessing,
            Status = JobStatus.Running,
            Attempts = attempts,
            StartedAt = DateTimeOffset.UtcNow
        };
        db.ProcessingJobs.Add(job);
        await db.SaveChangesAsync(ct);

        Stopwatch sw = Stopwatch.StartNew();

        try
        {
            document.ProcessingStatus = ProcessingStatus.Processing;
            AiAnalysisResult result = await ai.AnalyzeAsync(document.Title, text, ct);
            sw.Stop();

            db.LlmCallLogs.Add(new LLMCallLog
            {
                DocumentId = document.Id,
                Provider = ai.ProviderName,
                Model = ai.ModelName,
                PromptVersion = ai.PromptVersion,
                InputSize = text.Length,
                Output = JsonSerializer.Serialize(result),
                Status = LlmCallStatus.Success,
                LatencyMs = sw.ElapsedMilliseconds
            });

            RegulatoryEvent regulatoryEvent = new()
            {
                DocumentId = document.Id,
                Title = result.Title,
                Summary = result.Summary,
                ImpactLevel = result.ImpactLevel,
                ImpactExplanation = result.ImpactExplanation,
                EffectiveDate = result.EffectiveDate,
                Tags = [.. result.Tags]
            };
            db.RegulatoryEvents.Add(regulatoryEvent);

            document.ProcessingStatus = ProcessingStatus.Completed;

            job.Status = JobStatus.Succeeded;
            job.FinishedAt = DateTimeOffset.UtcNow;

            db.AuditLogs.Add(new AuditLog
            {
                Action = "RegulatoryEventCreated",
                EntityName = nameof(RegulatoryEvent),
                EntityId = regulatoryEvent.Id,
                Actor = ai.ProviderName,
                Details = regulatoryEvent.Title
            });

            await db.SaveChangesAsync(ct);

            IReadOnlyList<ClientImpact> impacts = await impactService.RecalculateAsync(regulatoryEvent.Id, ct);

            logger.LogInformation("AI analysis completed for document {DocumentId} in {LatencyMs} ms, {ImpactCount} clients affected",
                document.Id, sw.ElapsedMilliseconds, impacts.Count);
        }
        catch (Exception ex)
        {
            sw.Stop();
            logger.LogError(ex, "AI analysis failed for document {DocumentId}", document.Id);

            db.ChangeTracker.Clear();

            db.LlmCallLogs.Add(new LLMCallLog
            {
                DocumentId = document.Id,
                Provider = ai.ProviderName,
                Model = ai.ModelName,
                PromptVersion = ai.PromptVersion,
                InputSize = text.Length,
                Status = LlmCallStatus.Error,
                ErrorMessage = ex.Message,
                LatencyMs = sw.ElapsedMilliseconds
            });

            job.Status = JobStatus.Failed;
            job.ErrorMessage = ex.Message;
            job.FinishedAt = DateTimeOffset.UtcNow;
            db.ProcessingJobs.Update(job);

            await db.SaveChangesAsync(CancellationToken.None);
        }
    }
}
