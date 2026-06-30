using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;

namespace RegRadar.Infrastructure.Persistence;

public class RegRadarDbContextFactory : IDesignTimeDbContextFactory<RegRadarDbContext>
{
    public RegRadarDbContext CreateDbContext(string[] args)
    {
        var cs = Environment.GetEnvironmentVariable("ConnectionStrings__Postgres")
                 ?? "Host=localhost;Port=5432;Database=regradar;Username=regradar;Password=regradar";
        var options = new DbContextOptionsBuilder<RegRadarDbContext>()
            .UseNpgsql(cs).Options;
        return new RegRadarDbContext(options);
    }
}