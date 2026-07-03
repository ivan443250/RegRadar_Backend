using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

using RegRadar.Application.Abstractions;
using RegRadar.Application.Dtos;
using RegRadar.Application.Mapping;
using RegRadar.Infrastructure.Persistence;

namespace RegRadar.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class DocumentsController(RegRadarDbContext db, IDocumentProcessingService processing) : ControllerBase
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

    [HttpPost("upload")]
    public async Task<ActionResult> Upload(IFormFile file, CancellationToken ct)
    {
        if (file is null || file.Length == 0)
            return BadRequest(new { error = "File is required." });

        await using Stream stream = file.OpenReadStream();
        DocumentUploadResult result = await processing.UploadAsync(file.FileName, stream, ct);

        return result.Outcome switch
        {
            UploadOutcome.Created => CreatedAtAction(nameof(GetById), new { id = result.DocumentId }, new { documentId = result.DocumentId }),
            UploadOutcome.Duplicate => Conflict(new { documentId = result.DocumentId, error = "Document with the same content already exists." }),
            UploadOutcome.UnsupportedFormat => BadRequest(new { error = result.Error }),
            _ => StatusCode(StatusCodes.Status500InternalServerError, new { error = result.Error })
        };
    }
}
