namespace RegRadar.Infrastructure.TextProcessing;

public class ChunkingOptions
{
    public int ChunkSize { get; set; } = 1000;
    public int OverlapSize { get; set; } = 150;
}
