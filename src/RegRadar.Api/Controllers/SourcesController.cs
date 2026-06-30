using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

using RegRadar.Application.Dtos;
using RegRadar.Application.Mapping;
using RegRadar.Domain.Entities;
using RegRadar.Infrastructure.Persistence;

namespace RegRadar.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class SourcesController(RegRadarDbContext db) : ControllerBase
{
    [HttpGet]
    public async Task<ActionResult<IEnumerable<SourceDto>>> GetAll()
    {
        var sources = await db.Sources.AsNoTracking().ToListAsync();
        return Ok(sources.Select(s => s.ToDto()));
    }

    [HttpGet("{id:guid}")]
    public async Task<ActionResult<SourceDto>> GetById(Guid id)
    {
        var source = await db.Sources.FindAsync(id);
        return source is null ? NotFound() : source.ToDto();
    }

    [HttpPost]
    public async Task<ActionResult<SourceDto>> Create(CreateSourceRequest req)
    {
        var source = new Source
        {
            Name = req.Name,
            Type = req.Type,
            BaseUrl = req.BaseUrl
        };

        db.Sources.Add(source);
        await db.SaveChangesAsync();

        return CreatedAtAction(nameof(GetById), new { id = source.Id }, source.ToDto());
    }
}
