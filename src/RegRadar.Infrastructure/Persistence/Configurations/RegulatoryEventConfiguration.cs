using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

using RegRadar.Domain.Entities;

namespace RegRadar.Infrastructure.Persistence.Configurations;

public class RegulatoryEventConfiguration : IEntityTypeConfiguration<RegulatoryEvent>
{
    public void Configure(EntityTypeBuilder<RegulatoryEvent> e)
    {
        e.Property(r => r.Title).IsRequired().HasMaxLength(1024);
        e.Property(r => r.Summary).IsRequired();

        e.HasOne(r => r.Document)
            .WithOne()
            .HasForeignKey<RegulatoryEvent>(r => r.DocumentId)
            .OnDelete(DeleteBehavior.Cascade);

        e.HasIndex(r => r.DocumentId).IsUnique();
    }
}
