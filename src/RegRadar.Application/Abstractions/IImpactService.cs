using RegRadar.Domain.Entities;

namespace RegRadar.Application.Abstractions;

public interface IImpactService
{
    Task<IReadOnlyList<ClientImpact>> RecalculateAsync(Guid regulatoryEventId, CancellationToken ct = default);
}
