"""Human-readable validation report rendering."""

from document_translator.validation.report import DocumentValidationReport


def render_document_report(report: DocumentValidationReport) -> str:
    """Render a document validation report as plain text."""
    lines = [
        "Document Translation Validation Report",
        "=======================================",
        f"Source language: {report.source_language.value}",
        f"Target language: {report.target_language.value}",
        f"Status: {report.status.value.upper()}",
        f"Passed items: {report.pass_count}",
        f"Warnings: {report.warning_count}",
        f"Failures: {report.failure_count}",
    ]

    issues = [
        (item.location, issue)
        for item in report.items
        for issue in item.report.issues
    ]
    issues.extend(("document", issue) for issue in report.structural_issues)

    if not issues:
        lines.append("Issues: none")
        return "
".join(lines)

    lines.append("Issues:")
    for location, issue in issues:
        lines.append(f"- [{issue.severity.value.upper()}] {location}: {issue.code}")
        lines.append(f"  {issue.message}")
    return "
".join(lines)
