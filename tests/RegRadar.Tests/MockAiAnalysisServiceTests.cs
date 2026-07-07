using RegRadar.Application.Dtos;
using RegRadar.Domain.Enums;
using RegRadar.Infrastructure.Ai;

namespace RegRadar.Tests;

public class MockAiAnalysisServiceTests
{
    private readonly MockAiAnalysisService _service = new();

    private static AiAnalysisRequest Request(string title, string text) =>
        new(Guid.NewGuid(), title, text, [], []);

    [Theory]
    [InlineData(100, ImpactLevel.Low)]
    [InlineData(5000, ImpactLevel.Medium)]
    [InlineData(20000, ImpactLevel.High)]
    public async Task AnalyzeAsync_ImpactDependsOnTextLength(int length, ImpactLevel expected)
    {
        AiAnalysisResult result = await _service.AnalyzeAsync(Request("t", new string('x', length)));

        Assert.Equal(expected, result.ImpactLevel);
    }

    [Fact]
    public async Task AnalyzeAsync_IsDeterministic()
    {
        AiAnalysisResult first = await _service.AnalyzeAsync(Request("title", "text"));
        AiAnalysisResult second = await _service.AnalyzeAsync(Request("title", "text"));

        Assert.Equal(first.Summary, second.Summary);
        Assert.Equal(first.ImpactLevel, second.ImpactLevel);
        Assert.Equal(first.Tags, second.Tags);
    }

    [Fact]
    public async Task AnalyzeAsync_TruncatesLongSummary()
    {
        AiAnalysisResult result = await _service.AnalyzeAsync(Request("t", new string('x', 1000)));

        Assert.Equal(303, result.Summary.Length);
        Assert.EndsWith("...", result.Summary);
    }

    [Fact]
    public async Task AnalyzeAsync_ReturnsExtendedDetails()
    {
        ClientProfileDto client = new(Guid.NewGuid(), "ООО Тест", "62.01", "IT", CompanySize.Small,
            false, true, true, CashOperationsLevel.Low, ImpactLevel.Medium, "Малый бизнес");

        AiAnalysisResult result = await _service.AnalyzeAsync(
            new AiAnalysisRequest(Guid.NewGuid(), "t", "text", [], [client]));

        Assert.NotNull(result.Details);
        Assert.NotNull(result.Details!.ImpactScore);
        Assert.NotNull(result.Details.Review);
        Assert.Equal("MOCK", result.Details.Metadata?.Runtime);
        Assert.Single(result.Details.ClientRelevances);
        Assert.Single(result.Details.NotificationDrafts);
        Assert.Equal(client.Id.ToString(), result.Details.NotificationDrafts[0].ClientId);
        Assert.NotEmpty(result.Details.NotificationDrafts[0].Disclaimer);
    }
}
