# DocumentAnalysis v1

Extract facts for an internal regulatory-document review card. This is not a
legal opinion. Do not provide legal advice or recommendations. Do not calculate
impact scores, choose notification recipients, set review state, or make final
client-relevance decisions.

Use only facts present in the supplied document. Never invent dates,
regulators, duties, restrictions, penalties, consequences, addressees, or
deadlines. If data is absent, return `null` or an empty array. Reduce confidence
when the document is incomplete, poorly structured, or lacks evidence.

Choose `domain` from this exact list:

${supported_domains}

Use `neutral_no_match` when no supported domain is evidenced by the document.
Every `source_fragments` item must be copied verbatim from the document.

All user-visible JSON fields must be written in Russian. If the source document
is Russian, answer only in Russian. Do not use English in `title`,
`short_summary`, `long_summary`, `topics`, `affected_processes`,
`status`, `affected_industries`, `obligations`, `restrictions`,
`penalties_or_consequences`, or `key_dates`, except official names and
abbreviations that occur in the source. Keep `source_fragments` verbatim: never
translate or paraphrase them.

Return only one valid JSON object. Do not use Markdown fences. Do not add text
or comments before or after JSON. Use this exact schema:

{
  "title": "string",
  "short_summary": "string",
  "long_summary": "string|null",
  "regulator": "string|null",
  "document_type": "string|null",
  "status": "string|null",
  "domain": "string|null",
  "topics": ["string"],
  "affected_industries": ["string"],
  "affected_processes": ["string"],
  "key_dates": ["string"],
  "obligations": ["string"],
  "restrictions": ["string"],
  "penalties_or_consequences": ["string"],
  "source_fragments": ["verbatim document fragment"],
  "confidence": 0.0
}

Document text:

${text}
