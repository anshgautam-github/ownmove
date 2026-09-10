"""Assembles a profile + experiences + setup-answers + (optional) latest
Profile Analysis summary into everything a generator needs — a prompt-ready
text block for the LLM, and a handful of cheap deterministic booleans/lists
the mock generator uses directly.

Deliberately self-contained rather than importing
`app.profile_analysis.utils.context.ProfileContext`: that module's own
README states nothing outside `profile_analysis/` should import from it
except its router, so this module reads the same kind of signal
(leadership, research, portfolio, ...) with its own small, independent
implementation instead of reaching across the module boundary. The overlap
is a few lines of duplicated keyword-matching, not a shared dependency worth
coupling two otherwise-independent features over.

Pure Python, no I/O — the service layer fetches the raw rows (see
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
class RoadmapContext:
    profile: dict
    experiences: list[dict] = field(default_factory=list)
    # None means "no analysis has ever been run" — a normal state, not an
    # error; the prompt just proceeds without that extra signal.
    latest_analysis: dict | None = None

    # ---- setup answers, chosen on the setup screen (or replayed back
    # unchanged by the Regenerate action) ------------------------------
    target_role: str = ""
    timeline_months: int = 3
    weekly_commitment: int = 5
    primary_goal: str = "Get an Internship"

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
    def has_portfolio_signal(self) -> bool:
        return self.has_resume or self.has_github

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

    def to_prompt_text(self) -> str:
        """A compact, structured block — not a paragraph — so the LLM spends
        its attention on judgement, not on parsing prose. Every field the
        model is allowed to reason about must appear here — this is the
        entire evidence base for the roadmap."""
        lines = [
            f"Name: {self.full_name}",
            f"Headline: {self.profile.get('headline') or 'none provided'}",
            f"Bio: {(self.profile.get('bio') or 'none provided')[:400]}",
            f"Education: {self.profile.get('education_level') or 'unspecified'} — "
            f"{self.profile.get('degree') or 'unspecified'} in "
            f"{self.profile.get('major') or self.profile.get('branch') or 'unspecified'} at "
            f"{self.profile.get('college_name') or 'unspecified'} "
            f"(graduating {self.profile.get('graduation_year') or 'unspecified'}, "
            f"status: {self.profile.get('graduation_status') or 'unspecified'})",
            f"Profile's own target role: {self.profile.get('target_role') or 'unspecified'}",
            f"Target company: {self.profile.get('target_company') or 'unspecified'}",
            f"Career interests: {', '.join(self.career_interests) or 'none listed'}",
            f"Skills (profile-level): {', '.join(self.current_skills) or 'none listed'}",
            f"GitHub: {'yes' if self.has_github else 'no'}",
            f"Resume on file: {'yes' if self.has_resume else 'no'}",
            f"LinkedIn: {'yes' if self.profile.get('linkedin_url') else 'no'}",
            f"AI-generated profile summary (if any): "
            f"{self.profile.get('ai_profile_summary') or 'none generated yet'}",
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

        if self.latest_analysis:
            missing = [s.get("title") for s in (self.latest_analysis.get("missing_signals") or [])]
            contradictions = [
                c.get("contradiction") for c in (self.latest_analysis.get("profile_contradictions") or [])
            ]
            diagnosis = self.latest_analysis.get("profile_diagnosis") or {}
            lines.append(
                "Latest Profile Analysis on file: overall score "
                f"{self.latest_analysis.get('overall_score', 'unknown')}/100. "
                f"Strongest signal: {diagnosis.get('strongest_signal') or 'unknown'}. "
                f"Limiting factor: {diagnosis.get('limiting_factor') or 'unknown'}. "
                f"Missing signals: {', '.join(m for m in missing if m) or 'none'}. "
                f"Profile contradictions: {', '.join(c for c in contradictions if c) or 'none'}."
            )
            # career_signals and recruiter_signals are the two richest
            # per-item breakdowns Profile Analysis produces — surfacing them
            # here (not just the summary fields above) is what lets the
            # roadmap tell "already strong enough" (existing_strengths) apart
            # from "missing" (priority_gaps) at the level of a named signal,
            # not just a single overall score.
            career_signals = self.latest_analysis.get("career_signals") or []
            if career_signals:
                lines.append(
                    "Career signals observed by Profile Analysis: "
                    + "; ".join(
                        f"{s.get('signal', 'unknown')} ({s.get('strength', 'unknown')})"
                        for s in career_signals
                        if s.get("signal")
                    )
                )
            recruiter_signals = self.latest_analysis.get("recruiter_signals") or []
            if recruiter_signals:
                lines.append(
                    "Recruiter-visible signals observed by Profile Analysis: "
                    + "; ".join(
                        f"{s.get('signal', 'unknown')} ({s.get('status', 'unknown')})"
                        for s in recruiter_signals
                        if s.get("signal")
                    )
                )
        else:
            lines.append("Latest Profile Analysis on file: none generated yet.")

        lines.extend(
            [
                "--- Roadmap request ---",
                f"Chosen target role for this roadmap: {self.target_role}",
                f"Timeline: {self.timeline_months} months",
                f"Weekly time commitment: {self.weekly_commitment} hours/week",
                f"Primary goal: {self.primary_goal}",
            ]
        )
        return "\n".join(lines)
