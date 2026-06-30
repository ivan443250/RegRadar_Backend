using RegRadar.Domain.Common;
using RegRadar.Domain.Enums;

namespace RegRadar.Domain.Entities;

public class ClientProfile : BaseEntity
{
    public string CompanyName { get; set; } = null!;
    public string? Okved { get; set; }
    public string? Industry { get; set; }
    public CompanySize Size { get; set; }

    public bool HasForeignTrade { get; set; }
    public bool UsesOnlinePayments { get; set; }
    public bool HandlesPersonalData { get; set; }
    public CashOperationsLevel CashOperationsLevel { get; set; }

    public ImpactLevel RiskProfile { get; set; }
    public string? BankSegment { get; set; }

    public ICollection<ClientImpact> ClientImpacts { get; set; } = new List<ClientImpact>();
}