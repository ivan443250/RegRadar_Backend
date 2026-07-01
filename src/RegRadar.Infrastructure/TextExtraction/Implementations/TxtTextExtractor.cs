using System.Text;

namespace RegRadar.Infrastructure.TextExtraction.Implementations;

public class TxtTextExtractor : BaseTextExtractor
{
    protected override string NeedExtension => ".txt";

    public override async Task<string> ExtractAsync(Stream content, CancellationToken ct = default)
    {
        using StreamReader reader = new StreamReader(content, encoding: Encoding.UTF8);

        string text = await reader.ReadToEndAsync(ct);

        return text;
    }
}
