"""Field-level checks reusable across every agent's `validate()`.

A concrete agent's `validate()` should call `basic_field_checks()` first and
then layer on any source-specific rules (e.g. "this source always sets a
deadline; a missing one means the parser broke"), rather than re-deriving
generic checks like "title is non-empty" from scratch per source.
"""

from urllib.parse import urlparse

from app.ingestion.models.opportunity import NormalizedOpportunity
from app.ingestion.models.validation import ValidationIssue, ValidationResult

_MAX_PLAUSIBLE_TITLE_LENGTH = 200


def _looks_like_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def basic_field_checks(opportunity: NormalizedOpportunity) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if not opportunity.title.strip():
        issues.append(ValidationIssue(field="title", message="Title is empty.", severity="error"))
    elif len(opportunity.title) > _MAX_PLAUSIBLE_TITLE_LENGTH:
        issues.append(
            ValidationIssue(
                field="title",
                message=f"Title is implausibly long (>{_MAX_PLAUSIBLE_TITLE_LENGTH} chars) — parser likely grabbed the wrong element.",
                severity="warning",
            )
        )

    if not opportunity.source.strip() or not opportunity.source_id.strip():
        issues.append(
            ValidationIssue(
                field="source_id",
                message="Missing source/source_id — required for de-duplication.",
                severity="error",
            )
        )

    if opportunity.apply_url and not _looks_like_url(opportunity.apply_url):
        issues.append(
            ValidationIssue(field="apply_url", message="apply_url is not a valid http(s) URL.", severity="error")
        )

    if opportunity.logo_url and not _looks_like_url(opportunity.logo_url):
        issues.append(
            ValidationIssue(field="logo_url", message="logo_url is not a valid http(s) URL.", severity="warning")
        )

    if not opportunity.apply_url and not opportunity.description:
        issues.append(
            ValidationIssue(
                field="apply_url",
                message="Neither apply_url nor description is set — listing has no actionable content.",
                severity="warning",
            )
        )

    return issues


def to_validation_result(issues: list[ValidationIssue]) -> ValidationResult:
    has_errors = any(issue.severity == "error" for issue in issues)
    return ValidationResult(is_valid=not has_errors, issues=issues)
