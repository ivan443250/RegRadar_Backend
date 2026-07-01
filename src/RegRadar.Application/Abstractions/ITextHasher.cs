namespace RegRadar.Application.Abstractions;

public interface ITextHasher
{
    string GetHash(string key);
}
