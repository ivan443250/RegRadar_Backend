using RegRadar.Domain.Common;
using RegRadar.Domain.Enums;

namespace RegRadar.Domain.Entities;

public class Notification : BaseEntity
{
    public Guid RegulatoryEventId { get; set; }
    public RegulatoryEvent RegulatoryEvent { get; set; } = null!;

    public Guid? ClientProfileId { get; set; }
    public ClientProfile? ClientProfile { get; set; }

    public NotificationChannel Channel { get; set; }
    public NotificationStatus Status { get; set; } = NotificationStatus.Pending;

    public string? Payload { get; set; }
    public string? ExternalResponse { get; set; }
    public string? ErrorMessage { get; set; }
    public DateTimeOffset? SentAt { get; set; }
}