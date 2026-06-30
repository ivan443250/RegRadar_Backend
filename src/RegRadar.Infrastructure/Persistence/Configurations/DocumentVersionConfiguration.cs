using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

using RegRadar.Domain.Entities;

namespace RegRadar.Infrastructure.Persistence.Configurations;

public class DocumentVersionConfiguration : IEntityTypeConfiguration<DocumentVersion>
{
    public void Configure(EntityTypeBuilder<DocumentVersion> e)
    {
        e.Property(v => v.Text).IsRequired();
        e.Property(v => v.TextHash).IsRequired().HasMaxLength(64);

        e.HasIndex(v => new { v.DocumentId, v.TextHash }).IsUnique();

        e.HasMany(v => v.Chunks)
            .WithOne(c => c.DocumentVersion)
            .HasForeignKey(c => c.DocumentVersionId)
            .OnDelete(DeleteBehavior.Cascade);
    }
}
