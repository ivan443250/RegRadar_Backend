using RegRadar.Application.Dtos;

namespace RegRadar.Application.Abstractions;

public interface IRagChatService
{
    Task<RagChatAnswer> AskAsync(RagChatRequest request, CancellationToken ct = default);
}
