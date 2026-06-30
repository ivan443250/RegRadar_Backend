using RegRadar.Domain.Common;
using RegRadar.Domain.Enums;

namespace RegRadar.Domain.Entities;

public class Source : BaseEntity    
{
    public string Name { get; set; } = null!;
    public SourceType Type { get; set; }
    public string? BaseUrl { get; set; }
    public bool IsActive { get; set; } = true;

    
}
