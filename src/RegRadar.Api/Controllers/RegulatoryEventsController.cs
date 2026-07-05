using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

using RegRadar.Application.Abstractions;
using RegRadar.Application.Dtos;
using RegRadar.Application.Mapping;
using RegRadar.Infrastructure.Persistence;

namespace RegRadar.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class RegulatoryEventsController(RegRadarDbContext db, IImpactService impactService) : ControllerBase
{
    [HttpGet]
    public async Task<ActionResult<IEnumerable<RegulatoryEventDto>>> GetAll()
    {
        var events = await db.RegulatoryEvents.AsNoTracking().ToListAsync();
        return Ok(events.Select(e => e.ToDto()));
    }

    [HttpGet("{id:guid}")]
    public async Task<ActionResult<RegulatoryEventDto>> GetById(Guid id)
    {
        var ev = await db.RegulatoryEvents.FindAsync(id);
        return ev is null ? NotFound() : ev.ToDto();
    }

    [HttpGet("{id:guid}/impacts")]
    public async Task<ActionResult<IEnumerable<ClientImpactDto>>> GetImpacts(Guid id)
    {
        bool exists = await db.RegulatoryEvents.AnyAsync(e => e.Id == id);
        if (!exists)
            return NotFound();

        var impacts = await db.ClientImpacts.AsNoTracking()
            .Include(i => i.ClientProfile)
            .Where(i => i.RegulatoryEventId == id)
            .ToListAsync();

        return Ok(impacts.Select(i => i.ToDto()));
    }

    [HttpPost("{id:guid}/impacts/recalculate")]
    public async Task<ActionResult<IEnumerable<ClientImpactDto>>> RecalculateImpacts(Guid id, CancellationToken ct)
    {
        try
        {
            var impacts = await impactService.RecalculateAsync(id, ct);
            return Ok(impacts.Select(i => i.ToDto()));
        }
        catch (InvalidOperationException ex)
        {
            return NotFound(new { error = ex.Message });
        }
    }
}
