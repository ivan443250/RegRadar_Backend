# Version

`notification_generation_v1`

# Purpose

TODO: Generate safe informational notification drafts for reviewed client matches.

# Input variables

- `event_card`: TODO.
- `client_relevance`: TODO.

# Output schema

TODO: array of `NotificationDraft` JSON objects.

# Safety constraints

- Generate drafts only; never claim that a message has been published.
- Include the required non-legal-advice disclaimer.
- Avoid categorical obligations unless directly supported by evidence.
- Return valid JSON only, without Markdown.
