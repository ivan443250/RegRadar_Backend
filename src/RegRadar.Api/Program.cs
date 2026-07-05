using System.Text.Json.Serialization;

using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.EntityFrameworkCore;

using RegRadar.Infrastructure;
using RegRadar.Infrastructure.Persistence;

using Scalar.AspNetCore;

using Serilog;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddSerilog(cfg => cfg
    .WriteTo.Console()
    .Enrich.FromLogContext());

string postgres = builder.Configuration.GetConnectionString("Postgres")!;
string redis = builder.Configuration.GetConnectionString("Redis")!;

builder.Services.AddInfrastructure(builder.Configuration);

builder.Services.AddControllers()
    .AddJsonOptions(o => o.JsonSerializerOptions.Converters.Add(new JsonStringEnumConverter()));
builder.Services.AddOpenApi();

builder.Services.AddCors(options => 
    options.AddDefaultPolicy(policy => policy
    .AllowAnyOrigin()
    .AllowAnyHeader()
    .AllowAnyMethod()));

builder.Services.AddHealthChecks()
    .AddNpgSql(postgres, name: "postgres", tags: ["ready"])
    .AddRedis(redis, name: "redis", tags: ["ready"]);

var app = builder.Build();

using (IServiceScope startupScope = app.Services.CreateScope())
{
    try
    {
        var db = startupScope.ServiceProvider.GetRequiredService<RegRadarDbContext>();
        await db.Database.MigrateAsync();
        await SeedData.EnsureDemoClientsAsync(db);
    }
    catch (Exception ex)
    {
        app.Logger.LogWarning(ex, "Startup migration/seeding skipped: database unavailable");
    }
}

app.UseSerilogRequestLogging();
app.UseCors();

app.UseDefaultFiles();
app.UseStaticFiles();

app.MapOpenApi();
app.MapScalarApiReference();

app.MapHealthChecks("/health", new HealthCheckOptions() { Predicate = _ => false });

app.MapHealthChecks("/health/ready", new HealthCheckOptions()
{
    Predicate = check => check.Tags.Contains("ready")
});

app.MapControllers();

app.Run();