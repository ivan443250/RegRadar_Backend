using RegRadar.Application.Dtos;
using RegRadar.Domain.Entities;
using RegRadar.Domain.Enums;
using RegRadar.Infrastructure.Impact;

namespace RegRadar.Tests;

public class RuleBasedImpactAssessorTests
{
    private readonly RuleBasedImpactAssessor _assessor = new();

    private static ClientProfile Client(
        bool foreignTrade = false,
        bool onlinePayments = false,
        bool personalData = false,
        CashOperationsLevel cash = CashOperationsLevel.Low) => new()
    {
        CompanyName = "Тест",
        Size = CompanySize.Small,
        HasForeignTrade = foreignTrade,
        UsesOnlinePayments = onlinePayments,
        HandlesPersonalData = personalData,
        CashOperationsLevel = cash,
        RiskProfile = ImpactLevel.Low
    };

    [Fact]
    public void Assess_ForeignTradeText_AffectsImporter()
    {
        ImpactAssessment? result = _assessor.Assess("новые правила валютного контроля при импорте", Client(foreignTrade: true));

        Assert.NotNull(result);
        Assert.Equal(ImpactLevel.Medium, result.Level);
        Assert.Contains("внешнеэкономическая", result.Explanation);
    }

    [Fact]
    public void Assess_UnrelatedClient_ReturnsNull()
    {
        ImpactAssessment? result = _assessor.Assess("новые правила валютного контроля при импорте", Client(onlinePayments: true));

        Assert.Null(result);
    }

    [Fact]
    public void Assess_TwoFactors_ReturnsHigh()
    {
        string text = "изменения 115-ФЗ: контроль наличных и валютных операций";
        ImpactAssessment? result = _assessor.Assess(text, Client(foreignTrade: true, cash: CashOperationsLevel.High));

        Assert.NotNull(result);
        Assert.Equal(ImpactLevel.High, result.Level);
    }

    [Fact]
    public void Assess_EmptyText_ReturnsNull()
    {
        Assert.Null(_assessor.Assess("", Client(foreignTrade: true)));
    }

    [Fact]
    public void Assess_PersonalDataText_AffectsDataProcessor()
    {
        ImpactAssessment? result = _assessor.Assess("поправки 152-ФЗ об обработке персональных данных", Client(personalData: true));

        Assert.NotNull(result);
    }
}
