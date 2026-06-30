using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

using RegRadar.Application.Dtos;
using RegRadar.Application.Mapping;
using RegRadar.Domain.Entities;
using RegRadar.Infrastructure.Persistence;

namespace RegRadar.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class ClientProfilesController(RegRadarDbContext db) : ControllerBase
{
    [HttpGet]
    public async Task<ActionResult<IEnumerable<ClientProfileDto>>> GetAll()
    {
        var profiles = await db.ClientProfiles.AsNoTracking().ToListAsync();
        return Ok(profiles.Select(p => p.ToDto()));
    }

    [HttpGet("{id:guid}")]
    public async Task<ActionResult<ClientProfileDto>> GetById(Guid id)
    {
        var profile = await db.ClientProfiles.FindAsync(id);
        return profile is null ? NotFound() : profile.ToDto();
    }

    [HttpPost]
    public async Task<ActionResult<ClientProfileDto>> Create(CreateClientProfileRequest req)
    {
        var profile = new ClientProfile
        {
            CompanyName = req.CompanyName,
            Okved = req.Okved,
            Industry = req.Industry,
            Size = req.Size,
            HasForeignTrade = req.HasForeignTrade,
            UsesOnlinePayments = req.UsesOnlinePayments,
            HandlesPersonalData = req.HandlesPersonalData,
            CashOperationsLevel = req.CashOperationsLevel,
            RiskProfile = req.RiskProfile,
            BankSegment = req.BankSegment
        };

        db.ClientProfiles.Add(profile);
        await db.SaveChangesAsync();

        return CreatedAtAction(nameof(GetById), new { id = profile.Id }, profile.ToDto());
    }
}
