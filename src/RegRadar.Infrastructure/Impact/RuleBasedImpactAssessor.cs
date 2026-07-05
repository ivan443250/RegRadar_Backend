using System.Text.RegularExpressions;

using RegRadar.Application.Abstractions;
using RegRadar.Application.Dtos;
using RegRadar.Domain.Entities;
using RegRadar.Domain.Enums;

namespace RegRadar.Infrastructure.Impact;

public class RuleBasedImpactAssessor : IImpactAssessor
{
    private static readonly (Regex Pattern, Func<ClientProfile, bool> Applies, string Factor)[] Rules =
    [
        (new Regex(@"валют|импорт|экспорт|вэд|внешнеторг|нерезидент", RegexOptions.IgnoreCase | RegexOptions.Compiled),
            c => c.HasForeignTrade,
            "внешнеэкономическая деятельность"),

        (new Regex(@"персональн\w* данн|152-фз|роскомнадзор|локализаци", RegexOptions.IgnoreCase | RegexOptions.Compiled),
            c => c.HandlesPersonalData,
            "обработка персональных данных"),

        (new Regex(@"эквайринг|онлайн-платеж|интернет-магазин|интернет-торгов|платёжн|платежн", RegexOptions.IgnoreCase | RegexOptions.Compiled),
            c => c.UsesOnlinePayments,
            "онлайн-платежи"),

        (new Regex(@"наличн|115-фз|отмыван|обналич", RegexOptions.IgnoreCase | RegexOptions.Compiled),
            c => c.CashOperationsLevel == CashOperationsLevel.High,
            "наличные операции")
    ];

    public ImpactAssessment? Assess(string documentText, ClientProfile client)
    {
        if (string.IsNullOrWhiteSpace(documentText))
            return null;

        List<string> factors = Rules
            .Where(r => r.Pattern.IsMatch(documentText) && r.Applies(client))
            .Select(r => r.Factor)
            .ToList();

        if (factors.Count == 0)
            return null;

        ImpactLevel level = factors.Count >= 2 ? ImpactLevel.High : ImpactLevel.Medium;

        return new ImpactAssessment(level, $"Затронутые факторы: {string.Join(", ", factors)}");
    }
}
