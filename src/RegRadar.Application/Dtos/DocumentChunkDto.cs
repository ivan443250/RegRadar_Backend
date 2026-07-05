namespace RegRadar.Application.Dtos;

public record DocumentChunkDto(
    Guid Id,
    int ChunkIndex,
    string Content,
    int? TokenCount);

public record DocumentTextDto(
    Guid DocumentId,
    int VersionNumber,
    string Text);
