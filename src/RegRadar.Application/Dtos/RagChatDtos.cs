namespace RegRadar.Application.Dtos;

public record RagChatRequest(string Question, Guid? DocumentId, string? Audience);

public record RagChatSource(
    string Text,
    string? DocumentId,
    string? VersionId,
    string? ChunkId,
    double Score,
    string? Role);

public record RagChatAnswer(
    string Answer,
    string Audience,
    bool NoData,
    List<RagChatSource> Sources,
    string? SafetyNotice,
    string? Provider,
    string? Runtime,
    List<string> Warnings);
