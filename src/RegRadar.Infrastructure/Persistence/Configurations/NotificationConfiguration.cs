using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

using RegRadar.Domain.Entities;

namespace RegRadar.Infrastructure.Persistence.Configurations;

public class NotificationConfiguration : IEntityTypeConfiguration<Notification>
{
    public void Configure(EntityTypeBuilder<Notification> e)
    {
        e.HasOne(n => n.RegulatoryEvent)
            .WithMany(r => r.Notifications)
            .HasForeignKey(n => n.RegulatoryEventId)
            .OnDelete(DeleteBehavior.Cascade);

        e.HasOne(n => n.ClientProfile)
            .WithMany()
            .HasForeignKey(n => n.ClientProfileId)
            .OnDelete(DeleteBehavior.SetNull);
    }
}
