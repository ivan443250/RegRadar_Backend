using RegRadar.Domain.Enums;

namespace RegRadar.Application.Abstractions;

public interface ISourceIngestor
{
    SourceType Type { get; }

    Task<int> IngestAsync(CancellationToken ct = default);
}
