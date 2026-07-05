using Microsoft.Extensions.Options;

using RegRadar.Application.Abstractions;
using RegRadar.Workers.Options;

namespace RegRadar.Workers.BackgroundServices;

public class IngestionWorker(
    IServiceScopeFactory scopeFactory,
    IOptions<IngestionOptions> options,
    ILogger<IngestionWorker> logger) : BackgroundService
{
    private readonly IngestionOptions _options = options.Value;

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        logger.LogInformation("Ingestion worker started, interval {Minutes} min", _options.IntervalMinutes);

        await RunIterationAsync(stoppingToken);

        using PeriodicTimer timer = new(TimeSpan.FromMinutes(_options.IntervalMinutes));

        while (await timer.WaitForNextTickAsync(stoppingToken))
        {
            await RunIterationAsync(stoppingToken);
        }
    }

    private async Task RunIterationAsync(CancellationToken ct)
    {
        try
        {
            using IServiceScope scope = scopeFactory.CreateScope();

            var ingestors = scope.ServiceProvider.GetRequiredService<IEnumerable<ISourceIngestor>>().ToList();

            if (ingestors.Count == 0)
            {
                logger.LogInformation("Ingestion tick: no source ingestors registered");
                return;
            }

            foreach (ISourceIngestor ingestor in ingestors)
            {
                try
                {
                    int added = await ingestor.IngestAsync(ct);
                    logger.LogInformation("Source {SourceType}: {Added} new documents", ingestor.Type, added);
                }
                catch (OperationCanceledException)
                {
                    throw;
                }
                catch (Exception ex)
                {
                    logger.LogError(ex, "Ingestion failed for source {SourceType}", ingestor.Type);
                }
            }
        }
        catch (OperationCanceledException)
        {
            throw;
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Ingestion iteration failed");
        }
    }
}
