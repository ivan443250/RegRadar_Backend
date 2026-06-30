using RegRadar.Domain.Common;
using RegRadar.Domain.Enums;

namespace RegRadar.Domain.Entities;

public class Document : BaseEntity
{
    public Guid SourceId { get; set; }
    public Source Source { get; set; } = null!;

    public string Title { get; set; } = null!;
    public string? OriginalUrl { get; set; }
    public string? Regulator { get; set; }
    public DocumentType DocumentType { get; set; }
    public DateOnly? PublicationDate { get; set; }

    public DocumentStatus Status { get; set; } = DocumentStatus.Active;
    public ProcessingStatus ProcessingStatus { get; set; } = ProcessingStatus.Pending;

    public string? RawFilePath { get; set; }
    public string? RawHtml { get; set; }

    public string TextHash { get; set; } = null!;

    public ICollection<DocumentVersion> Versions { get; set; } = new List<DocumentVersion>();
}
