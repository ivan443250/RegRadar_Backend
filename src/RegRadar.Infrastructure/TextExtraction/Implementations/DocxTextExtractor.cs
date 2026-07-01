using DocumentFormat.OpenXml.Packaging;

namespace RegRadar.Infrastructure.TextExtraction.Implementations;

public class DocxTextExtractor : BaseTextExtractor
{
    protected override string NeedExtension => ".docx";

    public async override Task<string> ExtractAsync(Stream content, CancellationToken ct = default)
    {
        string text = await Task.Run(() =>
        {
            using WordprocessingDocument document = WordprocessingDocument.Open(content, false);
            return document?.MainDocumentPart?.Document?.Body?.InnerText ?? string.Empty;
        }, ct);

        return text;
    }
}
