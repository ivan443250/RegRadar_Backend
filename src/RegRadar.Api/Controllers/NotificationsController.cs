using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

using RegRadar.Application.Abstractions;
using RegRadar.Application.Dtos;
using RegRadar.Application.Mapping;
using RegRadar.Infrastructure.Persistence;

namespace RegRadar.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class NotificationsController(RegRadarDbContext db, INotificationSender sender) : ControllerBase
{
    [HttpGet]
    public async Task<ActionResult<IEnumerable<NotificationDto>>> GetAll()
    {
        var notifications = await db.Notifications.AsNoTracking()
            .OrderByDescending(n => n.CreatedAt)
            .ToListAsync();
        return Ok(notifications.Select(n => n.ToDto()));
    }

    [HttpGet("{id:guid}")]
    public async Task<ActionResult<NotificationDto>> GetById(Guid id)
    {
        var notification = await db.Notifications.FindAsync(id);
        return notification is null ? NotFound() : notification.ToDto();
    }

    [HttpPost("send")]
    public async Task<ActionResult<NotificationDto>> Send(SendNotificationRequest request, CancellationToken ct)
    {
        try
        {
            var notification = await sender.SendAsync(request.RegulatoryEventId, request.ClientProfileId, ct);
            return CreatedAtAction(nameof(GetById), new { id = notification.Id }, notification.ToDto());
        }
        catch (InvalidOperationException ex)
        {
            return NotFound(new { error = ex.Message });
        }
    }
}
