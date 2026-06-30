using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

using RegRadar.Domain.Entities;

namespace RegRadar.Infrastructure.Persistence.Configurations;

public class ClientProfileConfiguration : IEntityTypeConfiguration<ClientProfile>
{
    public void Configure(EntityTypeBuilder<ClientProfile> e)
    {
        e.Property(p => p.CompanyName).IsRequired().HasMaxLength(512);
        e.Property(p => p.Okved).HasMaxLength(32);
        e.Property(p => p.Industry).HasMaxLength(256);
        e.Property(p => p.BankSegment).HasMaxLength(128);
    }
}
