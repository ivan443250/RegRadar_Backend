using Microsoft.Extensions.Options;

using RegRadar.Application.Abstractions;

namespace RegRadar.Infrastructure.TextProcessing;

public class TextChunker : ITextChunker
{
    private readonly ChunkingOptions _options;

    public TextChunker(IOptions<ChunkingOptions> options)
    {
        _options = options.Value;

        if (_options.ChunkSize <= 0)
            throw new ArgumentException("ChunkSize must be positive.", nameof(options));

        if (_options.OverlapSize < 0 || _options.OverlapSize >= _options.ChunkSize)
            throw new ArgumentException("OverlapSize must be non-negative and less than ChunkSize.", nameof(options));
    }

    public IReadOnlyList<string> SliceToChunks(string text)
    {
        if (string.IsNullOrEmpty(text))
            return [];

        List<string> chunks = new((text.Length / _options.ChunkSize) + 1);
        int step = _options.ChunkSize - _options.OverlapSize;

        for (int i = 0; i < text.Length; i += step)
        {
            int end = Math.Min(i + _options.ChunkSize, text.Length);
            chunks.Add(text[i..end]);

            if (end == text.Length)
                break;
        }

        return chunks;
    }
}
