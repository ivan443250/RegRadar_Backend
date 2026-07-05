using RegRadar.Application.Dtos;

namespace RegRadar.Application.Abstractions;

public interface IDocumentProcessingService
{
    Task<DocumentUploadResult> IngestAsync(DocumentIngestRequest request, Stream content, CancellationToken ct = default);

    Task<DocumentUploadResult> ReprocessAsync(Guid documentId, CancellationToken ct = default);
}
