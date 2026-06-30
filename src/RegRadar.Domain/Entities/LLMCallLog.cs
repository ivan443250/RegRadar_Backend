using RegRadar.Domain.Common;
using RegRadar.Domain.Enums;

namespace RegRadar.Domain.Entities;

public class LLMCallLog : BaseEntity
{
    public Guid? DocumentId { get; set; }
    public Document? Document { get; set; }

    public string Provider { get; set; } = null!;
    public string Model { get; set; } = null!;
    public string? PromptVersion { get; set; }

    public int InputSize { get; set; }
    public string? Output { get; set; }

    public LlmCallStatus Status { get; set; }
    public string? ErrorMessage { get; set; }
    public long LatencyMs { get; set; }
}
