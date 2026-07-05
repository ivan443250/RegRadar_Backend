using System.Text.Json.Serialization;

using Microsoft.AspNetCore.Diagnostics.HealthChecks;

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

using (IServiceScope seedScope = app.Services.CreateScope())
{
    try
    {
        var db = seedScope.ServiceProvider.GetRequiredService<RegRadarDbContext>();
        await SeedData.EnsureDemoClientsAsync(db);
    }
    catch (Exception ex)
    {
        app.Logger.LogWarning(ex, "Demo client seeding skipped: database unavailable at startup");
    }
}

app.UseSerilogRequestLogging();
app.UseCors();

app.MapOpenApi();
app.MapScalarApiReference();

app.MapHealthChecks("/health", new HealthCheckOptions() { Predicate = _ => false });

app.MapHealthChecks("/health/ready", new HealthCheckOptions()
{
    Predicate = check => check.Tags.Contains("ready")
});

app.MapControllers();

app.MapGet("/", () => Results.Ok(new { service = "RegRadar", status = "ok" }));

app.Run();