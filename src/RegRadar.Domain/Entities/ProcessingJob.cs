using RegRadar.Domain.Common;
using RegRadar.Domain.Enums;

namespace RegRadar.Domain.Entities;

public class ProcessingJob : BaseEntity
{
    public Guid? DocumentId { get; set; }
    public Document? Document { get; set; }

    public JobType Type { get; set; }
    public JobStatus Status { get; set; } = JobStatus.Queued;

    public int Attempts { get; set; }
    public string? ErrorMessage { get; set; }

    public DateTimeOffset? StartedAt { get; set; }
    public DateTimeOffset? FinishedAt { get; set; }
}
