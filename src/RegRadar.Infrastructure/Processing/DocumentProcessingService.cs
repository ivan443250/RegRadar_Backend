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
    IOptions<StorageOptions> storageOptions,
    ILogger<DocumentProcessingService> logger) : IDocumentProcessingService
{
    private readonly StorageOptions _storage = storageOptions.Value;

    public async Task<DocumentUploadResult> UploadAsync(string fileName, Stream content, CancellationToken ct = default)
    {
        string extension = Path.GetExtension(fileName);
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

            Source source = await GetOrCreateUploadSourceAsync(ct);

            Document document = new()
            {
                Source = source,
                Title = Path.GetFileNameWithoutExtension(fileName),
                DocumentType = DocumentType.Unknown,
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
            await db.SaveChangesAsync(ct);

            await CompleteJobAsync(job, document.Id, ct);

            logger.LogInformation("Document {DocumentId} processed from {FileName}: {ChunkCount} chunks", document.Id, fileName, chunks.Count);

            await RunAiAnalysisAsync(document, normalized, ct);

            return DocumentUploadResult.Created(document.Id);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Document processing failed for {FileName}", fileName);

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

    private async Task<Source> GetOrCreateUploadSourceAsync(CancellationToken ct)
    {
        Source? source = await db.Sources.FirstOrDefaultAsync(s => s.Type == SourceType.UserUpload, ct);

        if (source is not null)
            return source;

        source = new Source
        {
            Name = "User Upload",
            Type = SourceType.UserUpload
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

    private async Task RunAiAnalysisAsync(Document document, string text, CancellationToken ct)
    {
        ProcessingJob job = new()
        {
            DocumentId = document.Id,
            Type = JobType.AiProcessing,
            Status = JobStatus.Running,
            Attempts = 1,
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

            db.RegulatoryEvents.Add(new RegulatoryEvent
            {
                DocumentId = document.Id,
                Title = result.Title,
                Summary = result.Summary,
                ImpactLevel = result.ImpactLevel,
                ImpactExplanation = result.ImpactExplanation,
                EffectiveDate = result.EffectiveDate,
                Tags = [.. result.Tags]
            });

            document.ProcessingStatus = ProcessingStatus.Completed;

            job.Status = JobStatus.Succeeded;
            job.FinishedAt = DateTimeOffset.UtcNow;

            await db.SaveChangesAsync(ct);

            logger.LogInformation("AI analysis completed for document {DocumentId} in {LatencyMs} ms", document.Id, sw.ElapsedMilliseconds);
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
