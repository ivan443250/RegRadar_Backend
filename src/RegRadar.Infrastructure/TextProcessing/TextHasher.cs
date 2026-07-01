using System.Security.Cryptography;
using System.Text;

using RegRadar.Application.Abstractions;

namespace RegRadar.Infrastructure.TextProcessing;

public class TextHasher : ITextHasher
{
    public string GetHash(string key)
    {
        byte[] bytes = Encoding.UTF8.GetBytes(key);
        byte[] hash = SHA256.HashData(bytes);
        return Convert.ToHexString(hash).ToLowerInvariant();
    }
}
