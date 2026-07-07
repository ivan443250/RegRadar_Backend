using System.Text.Json;

using RegRadar.Application.Dtos;

namespace RegRadar.Application.Serialization;

public static class AiDetailsSerializer
{
    private static readonly JsonSerializerOptions Options = new(JsonSerializerDefaults.Web);

    public static string Serialize(AiAnalysisDetails details) =>
        JsonSerializer.Serialize(details, Options);

    public static AiAnalysisDetails? Deserialize(string? json)
    {
        if (string.IsNullOrWhiteSpace(json))
            return null;

        try
        {
            return JsonSerializer.Deserialize<AiAnalysisDetails>(json, Options);
        }
        catch (JsonException)
        {
            return null;
        }
    }
}
