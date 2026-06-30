using Microsoft.EntityFrameworkCore;

using RegRadar.Domain.Entities;

namespace RegRadar.Infrastructure.Persistence;

public class RegRadarDbContext(DbContextOptions<RegRadarDbContext> options) : DbContext(options)
{
    public DbSet<Source> Sources => Set<Source>();
    public DbSet<Document> Documents => Set<Document>();
    public DbSet<DocumentVersion> DocumentVersions => Set<DocumentVersion>();
    public DbSet<DocumentChunk> DocumentChunks => Set<DocumentChunk>();
    public DbSet<RegulatoryEvent> RegulatoryEvents => Set<RegulatoryEvent>();
    public DbSet<ClientProfile> ClientProfiles => Set<ClientProfile>();
    public DbSet<ClientImpact> ClientImpacts => Set<ClientImpact>();
    public DbSet<Notification> Notifications => Set<Notification>();
    public DbSet<ProcessingJob> ProcessingJobs => Set<ProcessingJob>();
    public DbSet<LLMCallLog> LlmCallLogs => Set<LLMCallLog>();
    public DbSet<AuditLog> AuditLogs => Set<AuditLog>();

    protected override void OnModelCreating(ModelBuilder builder)
    {
        builder.ApplyConfigurationsFromAssembly(typeof(RegRadarDbContext).Assembly);

        var properties = builder.Model.GetEntityTypes().SelectMany(t => t.GetProperties()).Where(p => p.ClrType.IsEnum);
        foreach (var property in properties)
            property.SetProviderClrType(typeof(string));
    }
}
