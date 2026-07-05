using Microsoft.EntityFrameworkCore;

using RegRadar.Application.Abstractions;
using RegRadar.Application.Dtos;
using RegRadar.Domain.Entities;
using RegRadar.Infrastructure.Persistence;

namespace RegRadar.Infrastructure.Impact;

public class ImpactService(RegRadarDbContext db, IImpactAssessor assessor) : IImpactService
{
    public async Task<IReadOnlyList<ClientImpact>> RecalculateAsync(Guid regulatoryEventId, CancellationToken ct = default)
    {
        RegulatoryEvent ev = await db.RegulatoryEvents.FirstOrDefaultAsync(e => e.Id == regulatoryEventId, ct)
            ?? throw new InvalidOperationException($"Regulatory event {regulatoryEventId} not found.");

        string text = await db.DocumentVersions
            .Where(v => v.DocumentId == ev.DocumentId)
            .OrderByDescending(v => v.VersionNumber)
            .Select(v => v.Text)
            .FirstOrDefaultAsync(ct) ?? $"{ev.Title}\n{ev.Summary}";

        List<ClientProfile> clients = await db.ClientProfiles.ToListAsync(ct);

        List<ClientImpact> existing = await db.ClientImpacts
            .Where(i => i.RegulatoryEventId == ev.Id)
            .ToListAsync(ct);
        db.ClientImpacts.RemoveRange(existing);

        List<ClientImpact> created = [];

        foreach (ClientProfile client in clients)
        {
            ImpactAssessment? assessment = assessor.Assess(text, client);

            if (assessment is null)
                continue;

            created.Add(new ClientImpact
            {
                RegulatoryEventId = ev.Id,
                ClientProfileId = client.Id,
                ClientProfile = client,
                ImpactLevel = assessment.Level,
                Explanation = assessment.Explanation
            });
        }

        db.ClientImpacts.AddRange(created);
        await db.SaveChangesAsync(ct);

        return created;
    }
}
