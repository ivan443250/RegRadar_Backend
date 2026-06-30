using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

using RegRadar.Domain.Entities;

namespace RegRadar.Infrastructure.Persistence.Configurations;

public class ClientImpactConfiguration : IEntityTypeConfiguration<ClientImpact>
{
    public void Configure(EntityTypeBuilder<ClientImpact> e)
    {
        e.HasOne(c => c.RegulatoryEvent)
            .WithMany(r => r.ClientImpacts)
            .HasForeignKey(c => c.RegulatoryEventId)
            .OnDelete(DeleteBehavior.Cascade);

        e.HasOne(c => c.ClientProfile)
            .WithMany(p => p.ClientImpacts)
            .HasForeignKey(c => c.ClientProfileId)
            .OnDelete(DeleteBehavior.Restrict);

        e.HasIndex(c => new { c.RegulatoryEventId, c.ClientProfileId }).IsUnique();
    }
}
