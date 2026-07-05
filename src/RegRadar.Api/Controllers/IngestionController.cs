using Microsoft.AspNetCore.Mvc;

using RegRadar.Application.Abstractions;

namespace RegRadar.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class IngestionController(
    IEnumerable<ISourceIngestor> ingestors,
    ILogger<IngestionController> logger) : ControllerBase
{
    [HttpPost("run")]
    public async Task<ActionResult> Run(CancellationToken ct)
    {
        List<object> results = [];

        foreach (ISourceIngestor ingestor in ingestors)
        {
            try
            {
                int added = await ingestor.IngestAsync(ct);
                results.Add(new { source = ingestor.Type.ToString(), added });
            }
            catch (Exception ex)
            {
                logger.LogError(ex, "Manual ingestion failed for {Source}", ingestor.Type);
                results.Add(new { source = ingestor.Type.ToString(), error = ex.Message });
            }
        }

        return Ok(results);
    }
}
