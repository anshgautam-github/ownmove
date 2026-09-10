"""Assembles a profile + experiences row pair into everything a generator
needs — a prompt-ready text block for the LLM, and a handful of cheap
deterministic booleans/lists both generators use directly (so the mock
generator and the LLM prompt reason about the same facts).

Pure Python, no I/O. The service layer fetches the raw rows (see
services/repository.py); this module only ever transforms data already in
memory.
"""

from dataclasses import dataclass, field

_LEADERSHIP_HINTS = ("lead", "captain", "president", "founder", "head", "chair", "manager")
_HACKATHON_HINTS = ("hackathon", "hack day", "hack week")
_RESEARCH_HINTS = ("research", "paper", "publication", "lab assistant", "thesis")
_OPEN_SOURCE_HINTS = ("open source", "open-source", "oss", "pull request", "contributor")


def _contains_any(haystack: str, hints: tuple[str, ...]) -> bool:
    lowered = haystack.lower()
    return any(hint in lowered for hint in hints)


@dataclass
class ProfileContext:
    profile: dict
    experiences: list[dict] = field(default_factory=list)

    # ---- derived facts, computed once and reused by both generators -------

    @property
    def full_name(self) -> str:
        return self.profile.get("full_name") or "This student"

    @property
    def current_skills(self) -> list[str]:
        return list(self.profile.get("current_skills") or [])

    @property
    def career_interests(self) -> list[str]:
        return list(self.profile.get("career_interests") or [])

    @property
    def experience_skills(self) -> list[str]:
        seen: dict[str, None] = {}
        for experience in self.experiences:
            for skill in experience.get("skills_used") or []:
                seen.setdefault(skill, None)
        return list(seen)

    @property
    def all_skills(self) -> list[str]:
        seen: dict[str, None] = {}
        for skill in [*self.current_skills, *self.experience_skills]:
            seen.setdefault(skill, None)
        return list(seen)

    @property
    def has_github(self) -> bool:
        return bool(self.profile.get("github_url"))

    @property
    def has_resume(self) -> bool:
        return bool(self.profile.get("resume_url"))

    @property
    def has_leadership_signal(self) -> bool:
        if any("leadership" in interest.lower() for interest in self.career_interests):
            return True
        return any(
            _contains_any(experience.get("title") or "", _LEADERSHIP_HINTS)
            or _contains_any(experience.get("description") or "", _LEADERSHIP_HINTS)
            for experience in self.experiences
        )

    @property
    def has_hackathon_signal(self) -> bool:
        return any(
            _contains_any(f"{e.get('title', '')} {e.get('company', '')} {e.get('description', '')}", _HACKATHON_HINTS)
            for e in self.experiences
        )

    @property
    def has_research_signal(self) -> bool:
        if any("research" in interest.lower() for interest in self.career_interests):
            return True
        return any(
            _contains_any(f"{e.get('title', '')} {e.get('description', '')}", _RESEARCH_HINTS)
            for e in self.experiences
        )

    @property
    def has_open_source_signal(self) -> bool:
        if not self.has_github:
            return False
        return any(
            _contains_any(f"{e.get('title', '')} {e.get('description', '')}", _OPEN_SOURCE_HINTS)
            for e in self.experiences
        ) or any("open source" in s.lower() for s in self.all_skills)

    @property
    def has_portfolio_signal(self) -> bool:
        return self.has_resume or self.has_github

    def to_prompt_text(self) -> str:
        """A compact, structured block — not a paragraph — so the LLM spends
        its attention on judgement, not on parsing prose.

        Every field the model is allowed to reason about must appear here —
        this is the entire evidence base for the analysis. Fields the
        platform computes about itself (profile_score, ai_profile_summary
        from a prior run) are deliberately excluded so the model forms its
        own judgement instead of anchoring on a previous one.
        """
        lines = [
            f"Name: {self.full_name}",
            f"Headline: {self.profile.get('headline') or 'none provided'}",
            f"Bio: {(self.profile.get('bio') or 'none provided')[:400]}",
            f"Location: {self.profile.get('city') or 'unspecified'}, {self.profile.get('country') or 'unspecified'}",
            f"Education: {self.profile.get('education_level') or 'unspecified'} — "
            f"{self.profile.get('degree') or 'unspecified'} in "
            f"{self.profile.get('major') or self.profile.get('branch') or 'unspecified'} at "
            f"{self.profile.get('college_name') or 'unspecified'} "
            f"(graduating {self.profile.get('graduation_year') or 'unspecified'}, "
            f"status: {self.profile.get('graduation_status') or 'unspecified'})",
            f"Target role: {self.profile.get('target_role') or 'unspecified'}",
            f"Target company: {self.profile.get('target_company') or 'unspecified'}",
            f"Career interests: {', '.join(self.career_interests) or 'none listed'}",
            f"Skills (profile-level): {', '.join(self.current_skills) or 'none listed'}",
            f"GitHub: {'yes' if self.has_github else 'no'}",
            f"Resume on file: {'yes' if self.has_resume else 'no'}",
            f"LinkedIn: {'yes' if self.profile.get('linkedin_url') else 'no'}",
            f"Number of experiences logged: {len(self.experiences)}",
        ]
        for i, experience in enumerate(self.experiences, start=1):
            lines.append(
                f"Experience {i}: {experience.get('title') or 'Untitled'} at "
                f"{experience.get('company') or 'unknown org'} "
                f"({experience.get('experience_type') or 'unspecified type'}) — "
                f"skills used: {', '.join(experience.get('skills_used') or []) or 'none listed'}. "
                f"Description: {(experience.get('description') or 'none provided')[:300]}"
            )
        return "\n".join(lines)
