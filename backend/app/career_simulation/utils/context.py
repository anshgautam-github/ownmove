"""Assembles a profile + experiences + (optional) latest Profile Analysis +
a hypothetical scenario into everything a generator needs — a prompt-ready
text block for the LLM, and a handful of cheap deterministic booleans/lists
the mock generator uses directly.

Deliberately self-contained rather than importing
`app.career_roadmap.utils.context.RoadmapContext` or
`app.profile_analysis.utils.context.ProfileContext`: each of those modules'
own README restricts cross-module imports to their own router, so this
module reads the same kind of signal (skills, leadership, portfolio, ...)
with its own small, independent implementation instead of coupling three
otherwise-independent features together. The overlap is a few lines of
duplicated keyword-matching, not a shared dependency worth it.

The one thing genuinely specific to Career Simulation (and the reason this
isn't just a copy of RoadmapContext) is the KNOWN/HYPOTHETICAL split:
`to_prompt_text()` renders the real profile under an explicit "CURRENT
PROFILE (KNOWN)" heading and the simulated action under an explicit
"HYPOTHETICAL CHANGE (NOT REAL)" heading, so the model's context makes the
fact/hypothesis boundary structurally obvious rather than relying on prose
alone — see career_simulation/README.md's "Fact/hypothesis discipline"
section.

Pure Python, no I/O — the service layer fetches the raw rows (see
services/repository.py); this module only ever transforms data already in
memory.
"""

from dataclasses import dataclass, field

_LEADERSHIP_HINTS = ("lead", "captain", "president", "founder", "head", "chair", "manager")
_HACKATHON_HINTS = ("hackathon", "hack day", "hack week")
_RESEARCH_HINTS = ("research", "paper", "publication", "lab assistant", "thesis")
_OPEN_SOURCE_HINTS = ("open source", "open-source", "oss", "pull request", "contributor")

# Human-readable labels for each simulation type, used both in the prompt
# and available for the mock generator's narrative text.
SIMULATION_TYPE_LABELS: dict[str, str] = {
    "build_project": "Build a project",
    "gain_experience": "Gain experience (internship/research/freelance/professional work)",
    "learn_skill": "Learn a skill or technology",
    "certification": "Earn a certification",
    "open_source": "Contribute to an open-source project",
    "change_target_role": "Change target role",
    "compare_moves": "Compare two moves",
}


def _contains_any(haystack: str, hints: tuple[str, ...]) -> bool:
    lowered = haystack.lower()
    return any(hint in lowered for hint in hints)


def _format_scenario_input(simulation_type: str, scenario_input: dict) -> str:
    """Render whatever fields this simulation type's form actually
    collected, in a stable, readable order — never assumes every key is
    present (each type's form collects a different, small field set; see
    the module README), and never invents a value for a missing key."""
    if not scenario_input:
        return "(no additional scenario details provided)"
    # A fixed, sensible field order per type keeps the prompt's shape
    # predictable even though the underlying dict is free-form; anything
    # not in this list still gets rendered, just after the known fields.
    preferred_order: dict[str, list[str]] = {
        "build_project": ["project_topic", "description", "technologies", "scope", "estimated_hours"],
        "gain_experience": ["experience_type", "role_domain", "expected_work", "skills_involved", "duration"],
        "learn_skill": ["skill", "depth", "scope"],
        "certification": ["certification_name", "domain"],
        "open_source": ["technology_domain", "contribution_type"],
        "change_target_role": ["new_target_role"],
    }
    ordered_keys = preferred_order.get(simulation_type, [])
    lines = []
    seen = set()
    for key in ordered_keys:
        if key in scenario_input and scenario_input[key] not in (None, "", []):
            value = scenario_input[key]
            value_text = ", ".join(str(v) for v in value) if isinstance(value, list) else str(value)
            lines.append(f"- {key.replace('_', ' ')}: {value_text}")
            seen.add(key)
    for key, value in scenario_input.items():
        if key in seen or value in (None, "", []):
            continue
        value_text = ", ".join(str(v) for v in value) if isinstance(value, list) else str(value)
        lines.append(f"- {key.replace('_', ' ')}: {value_text}")
    return "\n".join(lines) if lines else "(no additional scenario details provided)"


@dataclass
class SimulationContext:
    profile: dict
    experiences: list[dict] = field(default_factory=list)
    # None means "no analysis has ever been run" — a normal state, not an
    # error; the prompt just proceeds without that extra signal.
    latest_analysis: dict | None = None

    # ---- the hypothetical being simulated -------------------------------
    simulation_type: str = "build_project"
    target_role: str = ""
    scenario_title: str = ""
    scenario_input: dict = field(default_factory=dict)

    # ---- derived facts, computed once and reused by both generators -------

    @property
    def full_name(self) -> str:
        return self.profile.get("full_name") or "This candidate"

    @property
    def current_target_role(self) -> str:
        """The candidate's REAL, current target role on file — distinct
        from `self.target_role`, which for a 'change_target_role'
        simulation is the hypothetical NEW role being evaluated."""
        return self.profile.get("target_role") or "unspecified"

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

    @property
    def latest_missing_signals(self) -> list[str]:
        """The most specific gap vocabulary available: Profile Analysis's
        own named missing signals, if one has ever been run. Used by both
        generators to decide whether a hypothetical action actually closes
        a previously-identified gap (`GapImpact`) rather than reasoning
        about gaps from scratch each time."""
        if not self.latest_analysis:
            return []
        return [s.get("title") for s in (self.latest_analysis.get("missing_signals") or []) if s.get("title")]

    def to_prompt_text(self) -> str:
        """A compact, structured block — not a paragraph — with the
        fact/hypothesis boundary made structurally explicit via two
        clearly labeled sections, rather than left to prose to convey."""
        known_lines = [
            "=== CURRENT PROFILE (KNOWN — real, on file today) ===",
            f"Name: {self.full_name}",
            f"Headline: {self.profile.get('headline') or 'none provided'}",
            f"Bio: {(self.profile.get('bio') or 'none provided')[:400]}",
            f"Education: {self.profile.get('education_level') or 'unspecified'} — "
            f"{self.profile.get('degree') or 'unspecified'} in "
            f"{self.profile.get('major') or self.profile.get('branch') or 'unspecified'} at "
            f"{self.profile.get('college_name') or 'unspecified'} "
            f"(graduating {self.profile.get('graduation_year') or 'unspecified'}, "
            f"status: {self.profile.get('graduation_status') or 'unspecified'})",
            f"Candidate's real, current target role: {self.current_target_role}",
            f"Target company: {self.profile.get('target_company') or 'unspecified'}",
            f"Career interests: {', '.join(self.career_interests) or 'none listed'}",
            f"Skills listed on profile: {', '.join(self.current_skills) or 'none listed'}",
            f"GitHub on file: {'yes' if self.has_github else 'no'}",
            f"Resume on file: {'yes' if self.has_resume else 'no'}",
            f"AI-generated profile summary (if any): "
            f"{self.profile.get('ai_profile_summary') or 'none generated yet'}",
            f"Number of experiences logged: {len(self.experiences)}",
        ]
        for i, experience in enumerate(self.experiences, start=1):
            known_lines.append(
                f"Experience {i}: {experience.get('title') or 'Untitled'} at "
                f"{experience.get('company') or 'unknown org'} "
                f"({experience.get('experience_type') or 'unspecified type'}) — "
                f"skills used: {', '.join(experience.get('skills_used') or []) or 'none listed'}. "
                f"Description: {(experience.get('description') or 'none provided')[:300]}"
            )

        if self.latest_analysis:
            diagnosis = self.latest_analysis.get("profile_diagnosis") or {}
            missing = self.latest_missing_signals
            known_lines.append(
                "Latest Profile Analysis on file: overall score "
                f"{self.latest_analysis.get('overall_score', 'unknown')}/100. "
                f"Strongest signal: {diagnosis.get('strongest_signal') or 'unknown'}. "
                f"Limiting factor: {diagnosis.get('limiting_factor') or 'unknown'}. "
                f"Named missing signals (the gaps a hypothetical action should be measured against): "
                f"{', '.join(missing) or 'none named'}."
            )
        else:
            known_lines.append("Latest Profile Analysis on file: none generated yet.")

        hypothetical_lines = [
            "",
            "=== HYPOTHETICAL CHANGE (NOT REAL — being simulated only, never write this back to the "
            "real profile) ===",
            f"Simulation type: {SIMULATION_TYPE_LABELS.get(self.simulation_type, self.simulation_type)}",
            f"Target role for this simulation: {self.target_role}",
        ]
        if self.simulation_type == "change_target_role":
            hypothetical_lines.append(
                f"This simulation asks: how would the SAME current profile above read against the "
                f"alternative target role '{self.target_role}', instead of the candidate's real, current "
                f"target role ('{self.current_target_role}')?"
            )
        hypothetical_lines.append(f"Scenario title: {self.scenario_title}")
        hypothetical_lines.append("Scenario details:")
        hypothetical_lines.append(_format_scenario_input(self.simulation_type, self.scenario_input))

        return "\n".join(known_lines + hypothetical_lines)
