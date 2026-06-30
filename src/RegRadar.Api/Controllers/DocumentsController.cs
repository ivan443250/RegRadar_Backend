using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

using RegRadar.Application.Dtos;
using RegRadar.Application.Mapping;
using RegRadar.Infrastructure.Persistence;

namespace RegRadar.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class DocumentsController(RegRadarDbContext db) : ControllerBase
{
    [HttpGet]
    public async Task<ActionResult<IEnumerable<DocumentDto>>> GetAll()
    {
        var documents = await db.Documents.AsNoTracking().ToListAsync();
        return Ok(documents.Select(d => d.ToDto()));
    }

    [HttpGet("{id:guid}")]
    public async Task<ActionResult<DocumentDto>> GetById(Guid id)
    {
        var document = await db.Documents.FindAsync(id);
        return document is null ? NotFound() : document.ToDto();
    }
}
