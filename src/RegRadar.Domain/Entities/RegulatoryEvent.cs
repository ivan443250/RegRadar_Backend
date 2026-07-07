using RegRadar.Domain.Common;
using RegRadar.Domain.Enums;

namespace RegRadar.Domain.Entities;

public class RegulatoryEvent : BaseEntity
{
    public Guid DocumentId { get; set; }
    public Document Document { get; set; } = null!;

    public string Title { get; set; } = null!;
    public string Summary { get; set; } = null!;

    public ImpactLevel ImpactLevel { get; set; }
    public string? ImpactExplanation { get; set; }
    public DateOnly? EffectiveDate { get; set; }

    public EventStatus Status { get; set; } = EventStatus.New;

    public List<string> Tags { get; set; } = new();

    public int? ImpactScore { get; set; }
    public string? Urgency { get; set; }
    public string? Domain { get; set; }
    public string? ReviewState { get; set; }
    public bool ReviewRequired { get; set; }
    public string? AiDetailsJson { get; set; }

    public ICollection<ClientImpact> ClientImpacts { get; set; } = new List<ClientImpact>();
    public ICollection<Notification> Notifications { get; set; } = new List<Notification>();
}
