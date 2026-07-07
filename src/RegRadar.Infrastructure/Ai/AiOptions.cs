namespace RegRadar.Infrastructure.Ai;

public class AiOptions
{
    public string Mode { get; set; } = "mock";
    public string BaseUrl { get; set; } = "http://ai:8000";
    public int TimeoutSeconds { get; set; } = 120;
}
