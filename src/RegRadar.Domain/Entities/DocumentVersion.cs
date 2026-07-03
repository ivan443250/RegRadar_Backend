using RegRadar.Domain.Common;

namespace RegRadar.Domain.Entities;

public class DocumentVersion : BaseEntity
{
    public Guid DocumentId { get; set; }
    public Document Document { get; set; } = null!;

    public int VersionNumber { get; set; }
    public string Text { get; set; } = null!;
    public string TextHash { get; set; } = null!;

    public ICollection<DocumentChunk> Chunks { get; set; } = new List<DocumentChunk>();
}
