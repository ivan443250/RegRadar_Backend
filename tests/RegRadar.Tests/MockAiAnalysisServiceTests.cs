using RegRadar.Application.Dtos;
using RegRadar.Domain.Enums;
using RegRadar.Infrastructure.Ai;

namespace RegRadar.Tests;

public class MockAiAnalysisServiceTests
{
    private readonly MockAiAnalysisService _service = new();

    [Theory]
    [InlineData(100, ImpactLevel.Low)]
    [InlineData(5000, ImpactLevel.Medium)]
    [InlineData(20000, ImpactLevel.High)]
    public async Task AnalyzeAsync_ImpactDependsOnTextLength(int length, ImpactLevel expected)
    {
        AiAnalysisResult result = await _service.AnalyzeAsync("t", new string('x', length));

        Assert.Equal(expected, result.ImpactLevel);
    }

    [Fact]
    public async Task AnalyzeAsync_IsDeterministic()
    {
        AiAnalysisResult first = await _service.AnalyzeAsync("title", "text");
        AiAnalysisResult second = await _service.AnalyzeAsync("title", "text");

        Assert.Equal(first.Summary, second.Summary);
        Assert.Equal(first.ImpactLevel, second.ImpactLevel);
        Assert.Equal(first.Tags, second.Tags);
    }

    [Fact]
    public async Task AnalyzeAsync_TruncatesLongSummary()
    {
        AiAnalysisResult result = await _service.AnalyzeAsync("t", new string('x', 1000));

        Assert.Equal(303, result.Summary.Length);
        Assert.EndsWith("...", result.Summary);
    }
}
