using RegRadar.Domain.Enums;

namespace RegRadar.Application.Dtos;

public record NotificationDto(
    Guid Id,
    Guid RegulatoryEventId,
    Guid? ClientProfileId,
    NotificationChannel Channel,
    NotificationStatus Status,
    string? Payload,
    string? ErrorMessage,
    DateTimeOffset? SentAt,
    DateTimeOffset CreatedAt);

public record SendNotificationRequest(Guid RegulatoryEventId, Guid? ClientProfileId);
