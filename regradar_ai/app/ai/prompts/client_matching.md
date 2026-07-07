# Version

`client_matching_v1`

# Purpose

TODO: Match a regulatory event to relevant client profiles.

# Input variables

- `event_card`: TODO.
- `client_profiles`: TODO.

# Output schema

TODO: array of `ClientRelevance` JSON objects.

# Safety constraints

- Do not infer unsupported client attributes.
- Explain every match using source evidence and supplied profile data.
- Do not provide legal advice.
- Return valid JSON only, without Markdown.
