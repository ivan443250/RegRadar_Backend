using RegRadar.Infrastructure.TextProcessing;

namespace RegRadar.Tests;

public class TextHasherTests
{
    private readonly TextHasher _hasher = new();

    [Fact]
    public void GetHash_Returns64LowercaseHexChars()
    {
        string hash = _hasher.GetHash("любой текст");

        Assert.Equal(64, hash.Length);
        Assert.Matches("^[0-9a-f]{64}$", hash);
    }

    [Fact]
    public void GetHash_IsDeterministic()
    {
        Assert.Equal(_hasher.GetHash("документ"), _hasher.GetHash("документ"));
    }

    [Fact]
    public void GetHash_DiffersForDifferentInput()
    {
        Assert.NotEqual(_hasher.GetHash("документ 1"), _hasher.GetHash("документ 2"));
    }
}
