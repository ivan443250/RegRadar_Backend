using RegRadar.Application.Dtos;
using RegRadar.Domain.Entities;

namespace RegRadar.Application.Abstractions;

public interface IImpactAssessor
{
    ImpactAssessment? Assess(string documentText, ClientProfile client);
}
