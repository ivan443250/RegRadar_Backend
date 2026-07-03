namespace RegRadar.Domain.Enums;

public enum ProcessingStatus
{
    Pending,
    Extracting,
    Chunking,
    AwaitingAi,
    Processing,
    Completed,
    Failed
}
