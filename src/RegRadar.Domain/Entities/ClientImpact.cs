using RegRadar.Domain.Common;
using RegRadar.Domain.Enums;

namespace RegRadar.Domain.Entities;

public class ClientImpact : BaseEntity
{
    public Guid RegulatoryEventId { get; set; }
    public RegulatoryEvent RegulatoryEvent { get; set; } = null!;

    public Guid ClientProfileId { get; set; }
    public ClientProfile ClientProfile { get; set; } = null!;

    public ImpactLevel ImpactLevel { get; set; }
    public string? Explanation { get; set; }
}