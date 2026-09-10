"""`validate()`'s output shape.

A `NormalizedOpportunity` can fail validation without the whole agent run
failing — the pipeline collects issues per-listing and keeps going, matching
"a single upstream page changing format" being the normal case for a scraper,
not an exceptional one.
"""

from typing import Literal

from pydantic import BaseModel, Field

ValidationSeverity = Literal["error", "warning"]


class ValidationIssue(BaseModel):
    field: str
    message: str
    severity: ValidationSeverity = "error"


class ValidationResult(BaseModel):
    is_valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)

    @classmethod
    def ok(cls, *, warnings: list[ValidationIssue] | None = None) -> "ValidationResult":
        return cls(is_valid=True, issues=warnings or [])

    @classmethod
    def failed(cls, issues: list[ValidationIssue]) -> "ValidationResult":
        return cls(is_valid=False, issues=issues)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]
