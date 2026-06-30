using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

using RegRadar.Domain.Entities;

namespace RegRadar.Infrastructure.Persistence.Configurations;

public class DocumentConfiguration : IEntityTypeConfiguration<Document>
{
    public void Configure(EntityTypeBuilder<Document> e)
    {
        e.Property(d => d.Title).IsRequired().HasMaxLength(1024);
        e.Property(d => d.TextHash).IsRequired().HasMaxLength(64);
        e.HasIndex(d => d.TextHash).IsUnique();

        e.HasOne(d => d.Source)
            .WithMany(s => s.Documents)
            .HasForeignKey(d => d.SourceId)
            .OnDelete(DeleteBehavior.Restrict);

        e.HasMany(d => d.Versions)
            .WithOne(v => v.Document)
            .HasForeignKey(v => v.DocumentId)
            .OnDelete(DeleteBehavior.Cascade);
    }
}