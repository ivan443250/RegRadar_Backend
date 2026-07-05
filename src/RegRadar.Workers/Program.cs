using RegRadar.Infrastructure;
using RegRadar.Workers.BackgroundServices;
using RegRadar.Workers.Options;

var builder = Host.CreateApplicationBuilder(args);

builder.Services.AddInfrastructure(builder.Configuration);
builder.Services.Configure<IngestionOptions>(builder.Configuration.GetSection("Ingestion"));
builder.Services.AddHostedService<IngestionWorker>();

var host = builder.Build();
host.Run();
