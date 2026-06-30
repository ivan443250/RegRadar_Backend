using Microsoft.AspNetCore.Diagnostics.HealthChecks;

using Scalar.AspNetCore;

using Serilog;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddSerilog(cfg => cfg
    .WriteTo.Console()
    .Enrich.FromLogContext());

string postgres = builder.Configuration.GetConnectionString("Postgres")!;
string redis = builder.Configuration.GetConnectionString("Redis")!;

builder.Services.AddControllers();
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