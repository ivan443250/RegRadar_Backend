using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

using RegRadar.Application.Abstractions;
using RegRadar.Application.Dtos;
using RegRadar.Domain.Enums;

namespace RegRadar.Infrastructure.Ingestion;

public class LocalSeedIngestor(
    IDocumentProcessingService processing,
    IOptions<SeedOptions> options,
    ILogger<LocalSeedIngestor> logger) : ISourceIngestor
{
    public SourceType Type => SourceType.Seed;

    public async Task<int> IngestAsync(CancellationToken ct = default)
    {
        string path = options.Value.SeedPath;

        if (!Directory.Exists(path))
        {
            logger.LogInformation("Seed directory '{Path}' not found, skipping", path);
            return 0;
        }

        int added = 0;

        foreach (string file in Directory.EnumerateFiles(path, "*.txt"))
        {
            ct.ThrowIfCancellationRequested();

            await using FileStream stream = File.OpenRead(file);

            DocumentIngestRequest request = new(
                FileName: Path.GetFileName(file),
                SourceType: SourceType.Seed,
                Title: Path.GetFileNameWithoutExtension(file).Replace('-', ' '),
                Regulator: "Демо-данные");

            DocumentUploadResult result = await processing.IngestAsync(request, stream, ct);

            if (result.Outcome == UploadOutcome.Created)
                added++;
            else if (result.Outcome == UploadOutcome.Failed)
                logger.LogWarning("Seed file '{File}' failed: {Error}", file, result.Error);
        }

        return added;
    }
}
