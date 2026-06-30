using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

using RegRadar.Application.Dtos;
using RegRadar.Application.Mapping;
using RegRadar.Infrastructure.Persistence;

namespace RegRadar.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class RegulatoryEventsController(RegRadarDbContext db) : ControllerBase
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
}
