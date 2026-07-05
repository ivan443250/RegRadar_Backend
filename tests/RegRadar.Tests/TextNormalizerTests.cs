using RegRadar.Infrastructure.TextProcessing;

namespace RegRadar.Tests;

public class TextNormalizerTests
{
    private readonly TextNormalizer _normalizer = new();

    [Fact]
    public void Normalize_UnifiesLineEndings()
    {
        string result = _normalizer.Normalize("line1\r\nline2\rline3\nline4");

        Assert.Equal("line1\nline2\nline3\nline4", result);
    }

    [Fact]
    public void Normalize_RemovesTrailingWhitespace()
    {
        string result = _normalizer.Normalize("line1   \nline2\t");

        Assert.Equal("line1\nline2", result);
    }

    [Fact]
    public void Normalize_CollapsesBlankLines()
    {
        string result = _normalizer.Normalize("a\n\n\n\n\nb");

        Assert.Equal("a\n\nb", result);
    }

    [Fact]
    public void Normalize_IsIdempotent()
    {
        string dirty = "  a\r\n\r\n\r\n\r\nb   \r\nc  ";

        string once = _normalizer.Normalize(dirty);
        string twice = _normalizer.Normalize(once);

        Assert.Equal(once, twice);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    public void Normalize_EmptyInput_ReturnsEmpty(string? input)
    {
        Assert.Equal(string.Empty, _normalizer.Normalize(input!));
    }
}
