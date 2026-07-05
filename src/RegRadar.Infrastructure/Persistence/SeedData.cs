using Microsoft.EntityFrameworkCore;

using RegRadar.Domain.Entities;
using RegRadar.Domain.Enums;

namespace RegRadar.Infrastructure.Persistence;

public static class SeedData
{
    public static async Task EnsureDemoClientsAsync(RegRadarDbContext db, CancellationToken ct = default)
    {
        if (await db.ClientProfiles.AnyAsync(ct))
            return;

        db.ClientProfiles.AddRange(
            new ClientProfile
            {
                CompanyName = "Лавка Онлайн (интернет-магазин)",
                Okved = "47.91",
                Industry = "Розничная интернет-торговля",
                Size = CompanySize.Small,
                HasForeignTrade = false,
                UsesOnlinePayments = true,
                HandlesPersonalData = true,
                CashOperationsLevel = CashOperationsLevel.Low,
                RiskProfile = ImpactLevel.Medium,
                BankSegment = "Малый бизнес"
            },
            new ClientProfile
            {
                CompanyName = "ИмпортТрейд (импортёр оборудования)",
                Okved = "46.69",
                Industry = "Оптовая торговля, ВЭД",
                Size = CompanySize.Medium,
                HasForeignTrade = true,
                UsesOnlinePayments = false,
                HandlesPersonalData = false,
                CashOperationsLevel = CashOperationsLevel.Medium,
                RiskProfile = ImpactLevel.High,
                BankSegment = "Средний бизнес"
            },
            new ClientProfile
            {
                CompanyName = "Сеть ресторанов «Тарелка»",
                Okved = "56.10",
                Industry = "Общественное питание",
                Size = CompanySize.Medium,
                HasForeignTrade = false,
                UsesOnlinePayments = true,
                HandlesPersonalData = true,
                CashOperationsLevel = CashOperationsLevel.High,
                RiskProfile = ImpactLevel.Medium,
                BankSegment = "Средний бизнес"
            },
            new ClientProfile
            {
                CompanyName = "КлаудСофт (IT/SaaS)",
                Okved = "62.01",
                Industry = "Разработка программного обеспечения",
                Size = CompanySize.Small,
                HasForeignTrade = true,
                UsesOnlinePayments = true,
                HandlesPersonalData = true,
                CashOperationsLevel = CashOperationsLevel.Low,
                RiskProfile = ImpactLevel.Low,
                BankSegment = "Малый бизнес"
            },
            new ClientProfile
            {
                CompanyName = "КэшМаркет (продуктовая розница)",
                Okved = "47.11",
                Industry = "Розничная торговля продуктами",
                Size = CompanySize.Large,
                HasForeignTrade = false,
                UsesOnlinePayments = false,
                HandlesPersonalData = false,
                CashOperationsLevel = CashOperationsLevel.High,
                RiskProfile = ImpactLevel.High,
                BankSegment = "Корпоративный"
            });

        await db.SaveChangesAsync(ct);
    }
}
