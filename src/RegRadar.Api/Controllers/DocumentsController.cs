using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

using RegRadar.Application.Abstractions;
using RegRadar.Application.Dtos;
using RegRadar.Application.Mapping;
using RegRadar.Domain.Enums;
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

        DocumentIngestRequest request = new(
            FileName: file.FileName,
            SourceType: SourceType.UserUpload);

        DocumentUploadResult result = await processing.IngestAsync(request, stream, ct);

        return result.Outcome switch
        {
            UploadOutcome.Created => CreatedAtAction(nameof(GetById), new { id = result.DocumentId }, new { documentId = result.DocumentId }),
            UploadOutcome.Duplicate => Conflict(new { documentId = result.DocumentId, error = "Document with the same content already exists." }),
            UploadOutcome.UnsupportedFormat => BadRequest(new { error = result.Error }),
            _ => StatusCode(StatusCodes.Status500InternalServerError, new { error = result.Error })
        };
    }

    [HttpGet("{id:guid}/text")]
    public async Task<ActionResult<DocumentTextDto>> GetText(Guid id)
    {
        var version = await db.DocumentVersions.AsNoTracking()
            .Where(v => v.DocumentId == id)
            .OrderByDescending(v => v.VersionNumber)
            .FirstOrDefaultAsync();

        return version is null
            ? NotFound()
            : new DocumentTextDto(id, version.VersionNumber, version.Text);
    }

    [HttpGet("{id:guid}/chunks")]
    public async Task<ActionResult<IEnumerable<DocumentChunkDto>>> GetChunks(Guid id)
    {
        var version = await db.DocumentVersions.AsNoTracking()
            .Where(v => v.DocumentId == id)
            .OrderByDescending(v => v.VersionNumber)
            .FirstOrDefaultAsync();

        if (version is null)
            return NotFound();

        var chunks = await db.DocumentChunks.AsNoTracking()
            .Where(c => c.DocumentVersionId == version.Id)
            .OrderBy(c => c.ChunkIndex)
            .Select(c => new DocumentChunkDto(c.Id, c.ChunkIndex, c.Content, c.TokenCount))
            .ToListAsync();

        return Ok(chunks);
    }

    [HttpPost("{id:guid}/reprocess")]
    public async Task<ActionResult> Reprocess(Guid id, CancellationToken ct)
    {
        DocumentUploadResult result = await processing.ReprocessAsync(id, ct);

        return result.Outcome switch
        {
            UploadOutcome.Created => Ok(new { documentId = result.DocumentId }),
            UploadOutcome.Duplicate => Conflict(new { documentId = result.DocumentId, error = "Document already has a regulatory event." }),
            _ => BadRequest(new { error = result.Error })
        };
    }
}
