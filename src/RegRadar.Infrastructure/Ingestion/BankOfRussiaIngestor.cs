using System.Text;
using System.Text.RegularExpressions;
using System.Xml.Linq;

using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

using RegRadar.Application.Abstractions;
using RegRadar.Application.Dtos;
using RegRadar.Domain.Enums;

namespace RegRadar.Infrastructure.Ingestion;

public class BankOfRussiaIngestor(
    IHttpClientFactory httpClientFactory,
    IDocumentProcessingService processing,
    IOptions<BankOfRussiaOptions> options,
    ILogger<BankOfRussiaIngestor> logger) : ISourceIngestor
{
    public const string HttpClientName = "BankOfRussia";

    private static readonly Regex HtmlTags = new("<[^>]+>", RegexOptions.Compiled);

    private readonly BankOfRussiaOptions _options = options.Value;

    public SourceType Type => SourceType.BankOfRussia;

    public async Task<int> IngestAsync(CancellationToken ct = default)
    {
        HttpClient client = httpClientFactory.CreateClient(HttpClientName);

        await using Stream rss = await client.GetStreamAsync(_options.RssUrl, ct);
        XDocument feed = await XDocument.LoadAsync(rss, LoadOptions.None, ct);

        int added = 0;

        foreach (XElement item in feed.Descendants("item"))
        {
            ct.ThrowIfCancellationRequested();

            string? title = item.Element("title")?.Value?.Trim();
            string? link = item.Element("link")?.Value?.Trim();
            string description = HtmlTags.Replace(item.Element("description")?.Value ?? string.Empty, " ").Trim();
            string? pubDateRaw = item.Element("pubDate")?.Value;

            if (string.IsNullOrWhiteSpace(title))
                continue;

            DateOnly? publicationDate = null;
            if (DateTimeOffset.TryParse(pubDateRaw, out DateTimeOffset pubDate))
                publicationDate = DateOnly.FromDateTime(pubDate.UtcDateTime);

            string content = $"{title}\n\n{description}";

            DocumentIngestRequest request = new(
                FileName: "cbr-rss-item.txt",
                SourceType: SourceType.BankOfRussia,
                Title: title,
                OriginalUrl: link,
                Regulator: "Банк России",
                PublicationDate: publicationDate,
                DocumentType: DocumentType.RegulatorLetter);

            await using MemoryStream stream = new(Encoding.UTF8.GetBytes(content));

            DocumentUploadResult result = await processing.IngestAsync(request, stream, ct);

            if (result.Outcome == UploadOutcome.Created)
                added++;
            else if (result.Outcome == UploadOutcome.Failed)
                logger.LogWarning("CBR item '{Title}' failed: {Error}", title, result.Error);
        }

        return added;
    }
}
