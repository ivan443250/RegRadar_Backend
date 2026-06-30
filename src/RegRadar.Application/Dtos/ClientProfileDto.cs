using RegRadar.Domain.Enums;

namespace RegRadar.Application.Dtos;

public record ClientProfileDto(
    Guid Id,
    string CompanyName,
    string? Okved,
    string? Industry,
    CompanySize Size,
    bool HasForeignTrade,
    bool UsesOnlinePayments,
    bool HandlesPersonalData,
    CashOperationsLevel CashOperationsLevel,
    ImpactLevel RiskProfile,
    string? BankSegment);

public record CreateClientProfileRequest(
    string CompanyName,
    string? Okved,
    string? Industry,
    CompanySize Size,
    bool HasForeignTrade,
    bool UsesOnlinePayments,
    bool HandlesPersonalData,
    CashOperationsLevel CashOperationsLevel,
    ImpactLevel RiskProfile,
    string? BankSegment);
