namespace RegRadar.Application.Abstractions;

public interface ITextChunker
{
    IReadOnlyList<string> SliceToChunks(string text);
}
