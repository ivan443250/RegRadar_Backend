using Microsoft.Extensions.Options;

using RegRadar.Infrastructure.TextProcessing;

namespace RegRadar.Tests;

public class TextChunkerTests
{
    private static TextChunker Create(int chunkSize, int overlap) =>
        new(Options.Create(new ChunkingOptions { ChunkSize = chunkSize, OverlapSize = overlap }));

    [Fact]
    public void SliceToChunks_EmptyText_ReturnsEmptyList()
    {
        Assert.Empty(Create(10, 2).SliceToChunks(""));
    }

    [Fact]
    public void SliceToChunks_ShortText_ReturnsSingleChunk()
    {
        var chunks = Create(100, 10).SliceToChunks("short");

        Assert.Single(chunks);
        Assert.Equal("short", chunks[0]);
    }

    [Fact]
    public void SliceToChunks_LongText_ChunksHaveOverlap()
    {
        string text = new string('a', 15) + new string('b', 15);
        var chunks = Create(10, 3).SliceToChunks(text);

        Assert.True(chunks.Count > 1);

        for (int i = 1; i < chunks.Count; i++)
        {
            string prevTail = chunks[i - 1][^3..];
            string currentHead = chunks[i][..3];
            Assert.Equal(prevTail, currentHead);
        }
    }

    [Fact]
    public void SliceToChunks_CoversWholeText()
    {
        string text = string.Concat(Enumerable.Range(0, 250).Select(i => (char)('а' + i % 30)));
        var chunks = Create(100, 20).SliceToChunks(text);

        Assert.StartsWith(chunks[0], text);
        Assert.EndsWith(chunks[^1], text);
    }

    [Theory]
    [InlineData(0, 0)]
    [InlineData(-5, 0)]
    [InlineData(10, 10)]
    [InlineData(10, 15)]
    [InlineData(10, -1)]
    public void Constructor_InvalidOptions_Throws(int chunkSize, int overlap)
    {
        Assert.Throws<ArgumentException>(() => Create(chunkSize, overlap));
    }
}
