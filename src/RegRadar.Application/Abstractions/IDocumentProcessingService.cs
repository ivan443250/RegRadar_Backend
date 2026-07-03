using RegRadar.Application.Dtos;

namespace RegRadar.Application.Abstractions;

public interface IDocumentProcessingService
{
    Task<DocumentUploadResult> UploadAsync(string fileName, Stream content, CancellationToken ct = default);
}
