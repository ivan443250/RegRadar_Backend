using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;

using RegRadar.Application.Abstractions;
using RegRadar.Infrastructure.Ai;
using RegRadar.Infrastructure.Impact;
using RegRadar.Infrastructure.Ingestion;
using RegRadar.Infrastructure.Notifications;
using RegRadar.Infrastructure.Persistence;
using RegRadar.Infrastructure.Processing;
using RegRadar.Infrastructure.TextExtraction.Implementations;
using RegRadar.Infrastructure.TextProcessing;

namespace RegRadar.Infrastructure;

public static class DependencyInjection
{
    public static IServiceCollection AddInfrastructure(this IServiceCollection services, IConfiguration config)
    {
        services.AddDbContext<RegRadarDbContext>(opt =>
            opt.UseNpgsql(config.GetConnectionString("Postgres")));

        services.AddTransient<ITextExtractor, TxtTextExtractor>();
        services.AddTransient<ITextExtractor, PdfTextExtractor>();
        services.AddTransient<ITextExtractor, DocxTextExtractor>();

        services.AddTransient<ITextNormalizer, TextNormalizer>();
        services.AddTransient<ITextHasher, TextHasher>();

        services.Configure<ChunkingOptions>(config.GetSection("Chunking"));
        services.AddTransient<ITextChunker, TextChunker>();

        services.Configure<StorageOptions>(config.GetSection("Storage"));
        services.AddScoped<IDocumentProcessingService, DocumentProcessingService>();

        services.Configure<AiOptions>(config.GetSection("Ai"));
        string aiMode = config.GetSection("Ai")["Mode"] ?? "mock";
        if (string.Equals(aiMode, "http", StringComparison.OrdinalIgnoreCase))
        {
            services.AddHttpClient(HttpAiAnalysisService.HttpClientName, (sp, client) =>
            {
                AiOptions ai = sp.GetRequiredService<IOptions<AiOptions>>().Value;
                client.BaseAddress = new Uri(ai.BaseUrl);
                client.Timeout = TimeSpan.FromSeconds(ai.TimeoutSeconds);
            });
            services.AddScoped<IAiAnalysisService, HttpAiAnalysisService>();
        }
        else
        {
            services.AddTransient<IAiAnalysisService, MockAiAnalysisService>();
        }

        services.Configure<BankOfRussiaOptions>(config.GetSection("BankOfRussia"));
        services.AddHttpClient(BankOfRussiaIngestor.HttpClientName, client =>
        {
            client.Timeout = TimeSpan.FromSeconds(30);
            client.DefaultRequestHeaders.UserAgent.ParseAdd("RegRadar/1.0");
        });
        services.AddScoped<ISourceIngestor, BankOfRussiaIngestor>();

        services.Configure<SeedOptions>(config.GetSection("Seed"));
        services.AddScoped<ISourceIngestor, LocalSeedIngestor>();

        services.AddTransient<IImpactAssessor, RuleBasedImpactAssessor>();
        services.AddScoped<IImpactService, ImpactService>();

        services.Configure<NotificationOptions>(config.GetSection("Notifications"));
        services.AddHttpClient(BitrixNotificationSender.HttpClientName, client =>
        {
            client.Timeout = TimeSpan.FromSeconds(30);
        });
        services.AddScoped<INotificationSender, BitrixNotificationSender>();

        return services;
    }
}
