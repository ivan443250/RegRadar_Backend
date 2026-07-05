using System.Text;
using System.Text.Json;

using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

using RegRadar.Application.Abstractions;
using RegRadar.Domain.Entities;
using RegRadar.Domain.Enums;
using RegRadar.Infrastructure.Persistence;

namespace RegRadar.Infrastructure.Notifications;

public class BitrixNotificationSender(
    RegRadarDbContext db,
    IHttpClientFactory httpClientFactory,
    IOptions<NotificationOptions> options,
    ILogger<BitrixNotificationSender> logger) : INotificationSender
{
    public const string HttpClientName = "Bitrix";

    private readonly NotificationOptions _options = options.Value;

    public async Task<Notification> SendAsync(Guid regulatoryEventId, Guid? clientProfileId, CancellationToken ct = default)
    {
        RegulatoryEvent ev = await db.RegulatoryEvents.FirstOrDefaultAsync(e => e.Id == regulatoryEventId, ct)
            ?? throw new InvalidOperationException($"Regulatory event {regulatoryEventId} not found.");

        ClientProfile? client = clientProfileId is null
            ? null
            : await db.ClientProfiles.FirstOrDefaultAsync(c => c.Id == clientProfileId, ct);

        string? explanation = client is null
            ? null
            : await db.ClientImpacts
                .Where(i => i.RegulatoryEventId == ev.Id && i.ClientProfileId == client.Id)
                .Select(i => i.Explanation)
                .FirstOrDefaultAsync(ct);

        string? originalUrl = await db.Documents
            .Where(d => d.Id == ev.DocumentId)
            .Select(d => d.OriginalUrl)
            .FirstOrDefaultAsync(ct);

        string payload = JsonSerializer.Serialize(new
        {
            eventId = ev.Id,
            title = ev.Title,
            summary = ev.Summary,
            impactLevel = ev.ImpactLevel.ToString(),
            effectiveDate = ev.EffectiveDate,
            tags = ev.Tags,
            sourceUrl = originalUrl,
            client = client?.CompanyName,
            clientExplanation = explanation
        });

        Notification notification = new()
        {
            RegulatoryEventId = ev.Id,
            ClientProfileId = client?.Id,
            Payload = payload
        };

        if (string.IsNullOrWhiteSpace(_options.BitrixWebhookUrl))
        {
            notification.Channel = NotificationChannel.Mock;
            notification.Status = NotificationStatus.Mocked;
            notification.SentAt = DateTimeOffset.UtcNow;
            logger.LogInformation("Mock notification for event {EventId}: {Payload}", ev.Id, payload);
        }
        else
        {
            notification.Channel = NotificationChannel.Bitrix;

            try
            {
                HttpClient http = httpClientFactory.CreateClient(HttpClientName);
                using StringContent content = new(payload, Encoding.UTF8, "application/json");
                using HttpResponseMessage response = await http.PostAsync(_options.BitrixWebhookUrl, content, ct);

                string body = await response.Content.ReadAsStringAsync(ct);
                notification.ExternalResponse = body.Length > 2000 ? body[..2000] : body;
                notification.SentAt = DateTimeOffset.UtcNow;

                if (response.IsSuccessStatusCode)
                {
                    notification.Status = NotificationStatus.Sent;
                }
                else
                {
                    notification.Status = NotificationStatus.Failed;
                    notification.ErrorMessage = $"HTTP {(int)response.StatusCode}";
                }
            }
            catch (Exception ex) when (ex is not OperationCanceledException)
            {
                notification.Status = NotificationStatus.Failed;
                notification.ErrorMessage = ex.Message;
                logger.LogError(ex, "Bitrix webhook call failed for event {EventId}", ev.Id);
            }
        }

        db.Notifications.Add(notification);
        db.AuditLogs.Add(new AuditLog
        {
            Action = "NotificationSend",
            EntityName = nameof(Notification),
            EntityId = notification.Id,
            Actor = "api",
            Details = $"channel={notification.Channel} status={notification.Status} event={ev.Id} client={client?.CompanyName ?? "-"}"
        });
        await db.SaveChangesAsync(ct);

        return notification;
    }
}
