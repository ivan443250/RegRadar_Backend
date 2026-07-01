namespace RegRadar.Application.Abstractions;

public interface ITextExtractor
{
    bool CanHandle(string fileExtension);
    Task<string> ExtractAsync(Stream content, CancellationToken ct = default);
}