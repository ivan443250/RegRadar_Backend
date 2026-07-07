namespace RegRadar.Application.Dtos;

public record AiKeyDate(string Date, string Meaning);

public record AiEvidenceFragment(
    string FragmentId,
    string Text,
    string SourceType,
    string? DocumentId,
    string? VersionId,
    string? ChunkId,
    string? SourceUrl,
    string EvidenceRole);

public record AiClientRelevance(
    string ClientId,
    string? ClientName,
    int RelevanceScore,
    string RelevanceLevel,
    List<string> MatchedFactors,
    string ExplanationForBank,
    string ExplanationForClient,
    List<string> EvidenceFragments,
    string? RecommendedNotificationType);

public record AiNotificationDraft(
    string? NotificationId,
    string ClientId,
    string ClientName,
    string Title,
    string ShortMessage,
    string FullMessage,
    string ClientFriendlyExplanation,
    string? SourceLink,
    string Disclaimer,
    string Priority,
    List<string> SourceChunkIds);

public record AiReviewInfo(string State, bool Required, string? NoDataReason);

public record AiAnalysisMetadata(
    string? Runtime,
    bool FallbackUsed,
    string? FallbackReason,
    string? ProcessingMode,
    string? ClientProfilesSource,
    List<string> Warnings,
    string? SelectedModel,
    string? RequestId,
    List<string> LlmCallIds,
    long? LatencyMs);

public class AiAnalysisDetails
{
    public int? ImpactScore { get; set; }
    public string? Urgency { get; set; }
    public double? Confidence { get; set; }
    public string? Domain { get; set; }
    public string? DocumentStatus { get; set; }
    public string? LongSummary { get; set; }
    public string? BankImpact { get; set; }
    public string? ClientImpact { get; set; }
    public List<string> Obligations { get; set; } = [];
    public List<string> Restrictions { get; set; } = [];
    public List<string> PenaltiesOrConsequences { get; set; } = [];
    public List<string> AffectedProcesses { get; set; } = [];
    public List<string> PossibleConsequences { get; set; } = [];
    public List<string> AffectedIndustries { get; set; } = [];
    public List<AiKeyDate> KeyDates { get; set; } = [];
    public List<string> SourceFragments { get; set; } = [];
    public List<AiEvidenceFragment> Evidence { get; set; } = [];
    public List<AiClientRelevance> ClientRelevances { get; set; } = [];
    public List<AiNotificationDraft> NotificationDrafts { get; set; } = [];
    public AiReviewInfo? Review { get; set; }
    public AiAnalysisMetadata? Metadata { get; set; }
}
