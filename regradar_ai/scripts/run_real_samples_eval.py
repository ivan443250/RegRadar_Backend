"""Print a compact baseline report for the real-document manifest."""

from app.evaluation import (
    load_real_samples_manifest,
    run_full_analysis_for_sample,
)


def _sample_status(sample, analysis) -> str:
    checks: list[bool] = []
    if sample.document_type_expected:
        checks.append(
            (analysis.document_analysis.document_type or "").casefold()
            == sample.document_type_expected.casefold()
        )
    if sample.topics_expected:
        actual_topics = " ".join(analysis.document_analysis.topics).casefold()
        checks.append(
            any(topic.casefold() in actual_topics for topic in sample.topics_expected)
        )
    if sample.domain_expected:
        checks.append(analysis.document_analysis.domain == sample.domain_expected)
    allowed_levels = set(sample.impact_levels_allowed)
    if sample.impact_level_expected:
        allowed_levels.add(sample.impact_level_expected)
    if allowed_levels:
        checks.append(analysis.impact_assessment.impact_level in allowed_levels)
    return "OK" if all(checks) else "NEEDS_RULE_UPDATE"


def main() -> None:
    samples = load_real_samples_manifest(enabled_only=True)
    if not samples:
        print(
            "Real samples manifest is empty. Add UTF-8 TXT files to "
            "data/real_samples/txt and describe them in manifest.json."
        )
        return

    headers = (
        "id",
        "expected domain",
        "detected topics",
        "impact",
        "clients",
        "notifications",
        "status",
    )
    rows: list[tuple[str, ...]] = []
    for sample in samples:
        analysis = run_full_analysis_for_sample(sample)
        rows.append(
            (
                sample.id,
                sample.domain_expected or "—",
                ", ".join(analysis.document_analysis.topics),
                analysis.impact_assessment.impact_level,
                str(len(analysis.client_relevance)),
                str(len(analysis.notification_drafts)),
                _sample_status(sample, analysis),
            )
        )

    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]
    print(" | ".join(value.ljust(widths[index]) for index, value in enumerate(headers)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


if __name__ == "__main__":
    main()
