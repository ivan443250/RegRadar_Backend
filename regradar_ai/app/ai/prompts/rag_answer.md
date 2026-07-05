# Version

`rag_answer_v1`

# Purpose

TODO: Produce an evidence-grounded answer from retrieved regulatory fragments.

# Input variables

- `question`: TODO.
- `retrieved_fragments`: TODO.

# Output schema

TODO: grounded answer JSON with evidence references.

# Safety constraints

- Use only supplied evidence fragments.
- State when the provided context is insufficient.
- Do not provide legal advice.
- Return valid JSON only, without Markdown.
