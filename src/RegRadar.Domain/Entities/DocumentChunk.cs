using RegRadar.Domain.Common;

namespace RegRadar.Domain.Entities;

public class DocumentChunk : BaseEntity
{
    public Guid DocumentVersionId { get; set; }
    public DocumentVersion DocumentVersion { get; set; } = null!;

    public int DocumentIndex { get; set; }
    public string Content { get; set; } = null!;
    public int? TokenCount { get; set; }
}
