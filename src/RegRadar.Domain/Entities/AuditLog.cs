using RegRadar.Domain.Common;

namespace RegRadar.Domain.Entities;

public class AuditLog : BaseEntity
{
    public string Action { get; set; } = null!;
    public string? EntityName { get; set; }
    public Guid? EntityId { get; set; }
    public string? Actor { get; set; }
    public string? Details { get; set; }
}
