namespace RegRadar.Application.Dtos;

public enum UploadOutcome
{
    Created,
    Duplicate,
    UnsupportedFormat,
    Failed
}

public record DocumentUploadResult(UploadOutcome Outcome, Guid? DocumentId, string? Error)
{
    public static DocumentUploadResult Created(Guid id) => new(UploadOutcome.Created, id, null);
    public static DocumentUploadResult Duplicate(Guid id) => new(UploadOutcome.Duplicate, id, null);
    public static DocumentUploadResult UnsupportedFormat(string extension) => new(UploadOutcome.UnsupportedFormat, null, $"Unsupported file format: {extension}");
    public static DocumentUploadResult Failed(string error) => new(UploadOutcome.Failed, null, error);
}
