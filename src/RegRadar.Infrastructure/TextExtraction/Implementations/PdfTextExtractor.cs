using System.Text;

using UglyToad.PdfPig;
using UglyToad.PdfPig.Content;

namespace RegRadar.Infrastructure.TextExtraction.Implementations;

public class PdfTextExtractor : BaseTextExtractor
{
    protected override string NeedExtension => ".pdf";

    public async override Task<string> ExtractAsync(Stream content, CancellationToken ct = default)
    {
        string text = await Task.Run(() =>
        {
            using PdfDocument document = PdfDocument.Open(content);
            StringBuilder sb = new();

            foreach (Page page in document.GetPages())
            {
                sb.Append(page.Text);
                sb.Append("\n");
            }

            return sb.ToString();
        }, ct);

        return text;
    }
}
