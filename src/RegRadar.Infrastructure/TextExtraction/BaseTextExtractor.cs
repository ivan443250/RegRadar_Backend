using RegRadar.Application.Abstractions;

namespace RegRadar.Infrastructure.TextExtraction;

public abstract class BaseTextExtractor : ITextExtractor
{
    protected abstract string NeedExtension { get; }

    public bool CanHandle(string fileExtension)
    {
        return string.Equals(fileExtension, NeedExtension, StringComparison.OrdinalIgnoreCase);
    }

    public abstract Task<string> ExtractAsync(Stream content, CancellationToken ct = default);
}
