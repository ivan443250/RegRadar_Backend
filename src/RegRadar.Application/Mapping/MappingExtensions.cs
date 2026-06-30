using RegRadar.Application.Dtos;
using RegRadar.Domain.Entities;

namespace RegRadar.Application.Mapping;

public static class MappingExtensions
{
    public static SourceDto ToDto(this Source s) =>
        new(s.Id, s.Name, s.Type, s.BaseUrl, s.IsActive);

    public static DocumentDto ToDto(this Document d) =>
        new(d.Id, d.SourceId, d.Title, d.OriginalUrl, d.Regulator, d.DocumentType,
            d.PublicationDate, d.Status, d.ProcessingStatus, d.CreatedAt);

    public static RegulatoryEventDto ToDto(this RegulatoryEvent r) =>
        new(r.Id, r.DocumentId, r.Title, r.Summary, r.ImpactLevel, r.ImpactExplanation,
            r.EffectiveDate, r.Status, r.Tags, r.CreatedAt);

    public static ClientProfileDto ToDto(this ClientProfile p) =>
        new(p.Id, p.CompanyName, p.Okved, p.Industry, p.Size, p.HasForeignTrade,
            p.UsesOnlinePayments, p.HandlesPersonalData, p.CashOperationsLevel,
            p.RiskProfile, p.BankSegment);
}
