using System.Text;
using System.Text.RegularExpressions;

using RegRadar.Application.Abstractions;

namespace RegRadar.Infrastructure.TextProcessing;

public class TextNormalizer : ITextNormalizer
{
    private static readonly Regex BlankLines = new("\n{3,}", RegexOptions.Compiled);

    public string Normalize(string text)
    {
        if (string.IsNullOrEmpty(text))
            return string.Empty;

        string unified = text.Replace("\r\n", "\n").Replace("\r", "\n");
        string formC = unified.Normalize(NormalizationForm.FormC);

        string[] lines = formC.Split('\n');
        for (int i = 0; i < lines.Length; i++)
            lines[i] = lines[i].TrimEnd();

        string joined = string.Join('\n', lines);
        string collapsed = BlankLines.Replace(joined, "\n\n");

        return collapsed.Trim();
    }
}

