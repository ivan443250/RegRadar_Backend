using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;

using RegRadar.Infrastructure.Persistence;

namespace RegRadar.Infrastructure;

public static class DependencyInjection
{
    public static IServiceCollection AddInfrastructure(this IServiceCollection services, IConfiguration config)
    {
        services.AddDbContext<RegRadarDbContext>(opt =>
            opt.UseNpgsql(config.GetConnectionString("Postgres")));
        return services;
    }
}
