using Microsoft.AspNetCore.Mvc;

using RegRadar.Application.Abstractions;
using RegRadar.Application.Dtos;

namespace RegRadar.Api.Controllers;

[ApiController]
[Route("api/chat")]
public class ChatController(IRagChatService chat, ILogger<ChatController> logger) : ControllerBase
{
    [HttpPost]
    public async Task<ActionResult<RagChatAnswer>> Ask(RagChatRequest request, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(request.Question))
            return BadRequest(new { error = "question must not be empty" });

        try
        {
            return Ok(await chat.AskAsync(request, ct));
        }
        catch (Exception ex) when (ex is HttpRequestException or InvalidOperationException or TaskCanceledException)
        {
            logger.LogError(ex, "RAG chat request failed");
            return StatusCode(502, new { error = "AI-сервис недоступен, попробуйте позже." });
        }
    }
}
