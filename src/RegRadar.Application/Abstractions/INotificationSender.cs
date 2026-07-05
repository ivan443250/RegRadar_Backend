using RegRadar.Domain.Entities;

namespace RegRadar.Application.Abstractions;

public interface INotificationSender
{
    Task<Notification> SendAsync(Guid regulatoryEventId, Guid? clientProfileId, CancellationToken ct = default);
}
