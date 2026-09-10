"""Deterministic, zero-dependency generator.

Runs with no API key and no network call — every field is computed from
rule-based heuristics against the actual profile/experience data in
`ProfileContext`. This exists so the whole feature (route, persistence,
frontend cards, loading/empty/error states) is testable end-to-end the
moment this module ships, before anyone adds an OPENAI_API_KEY. Once a key
is configured, `factory.py` switches to `LangGraphAnalysisGenerator` with no
other code changing — see that file.

Every heuristic here is intentionally simple and inspectable: no field is
ever a "trust me" number. `overall_score`, `score_breakdown`, and
`growth_simulation` below are all placeholders that `utils/scoring.py`'s
`reconcile()` fully overwrites with its own itemized math — this generator
only needs to produce the honest, evidence-grounded *inputs* to that math
(career_signals, missing_signals, profile_contradictions,
recruiter_signals), not the final numbers themselves.
"""

from app.profile_analysis.schemas.analysis import (
    AnalysisContent,
    CareerSignal,
    GrowthSimulation,
    HighestRoiRecommendation,
    MissingSignal,
    ProfileContradiction,
    ProfileDiagnosis,
    RecruiterSignal,
    ScoreBreakdown,
)
from app.profile_analysis.services.generators.base import BaseAnalysisGenerator
from app.profile_analysis.utils.context import ProfileContext
from app.profile_analysis.utils.scoring import reconcile

_BUILDER_SKILLS = {"react", "javascript", "python", "node.js", "sql", "git", "figma", "excel"}
_PRODUCT_HINTS = ("product", "user research", "roadmap", "stakeholder", "customer", "ux", "requirements", "wireframe")
_COMMUNITY_HINTS = ("community", "meetup", "volunteer", "organize", "mentor", "outreach", "club")
_TECHNICAL_DEPTH_SKILLS = {
    "algorithms", "data structures", "system design", "ml", "machine learning",
    "distributed systems", "concurrency",
}
_SKILL_CATEGORY_BUCKETS: dict[str, set[str]] = {
    "frontend": {"react", "javascript", "html", "css", "figma", "typescript"},
    "backend": {"node.js", "sql", "api", "django", "flask", "java"},
    "data/ml": {"python", "sql", "ml", "machine learning", "pandas", "tensorflow"},
    "design": {"figma", "ui/ux", "design"},
}

# ---- career signals: fixed vocabulary, always all 6, honestly labeled ----
#
# Unlike the earlier "Career DNA" design, this section never filters signals
# down to a top-N subset and never synthesizes a single personality
# "archetype" label — see CareerSignal's docstring in schemas/analysis.py.
# All 6 signals are always reported; one genuinely having no supporting
# evidence is itself a real, useful finding ("not observed"), not something
# to hide by omission.


def _strength_for(confidence: int) -> str:
    if confidence >= 70:
        return "strong"
    if confidence >= 45:
        return "moderate"
    if confidence >= 25:
        return "emerging"
    return "not observed"


# ---- profile contradictions: stated goal vs. observed evidence -----------
#
# Generalizes what an earlier iteration of this feature called "Career
# Blind Spots": any place the profile's stated direction and its logged
# evidence measurably diverge, not only a skill-category mismatch.
_CATEGORY_KEYWORDS: dict[str, set[str]] = {
    "Frontend": {"react", "javascript", "typescript", "html", "css", "vue", "angular", "next.js", "tailwind", "figma", "ui/ux"},
    "Backend": {"node.js", "django", "flask", "java", "spring", "api", "microservices", "go", "ruby", "rails", "c#", ".net", "sql"},
    "Machine Learning": {
        "machine learning", "ml", "ai/ml", "tensorflow", "pytorch", "nlp", "llm", "rag",
        "langchain", "langgraph", "deep learning", "computer vision", "data science",
    },
    "Data": {"data analysis", "pandas", "numpy", "data engineering", "etl", "spark"},
    "Mobile": {"swift", "kotlin", "react native", "flutter", "android", "ios"},
}
_CATEGORY_ALIASES: dict[str, set[str]] = {
    "Frontend": {"frontend", "front-end", "front end", "ui developer", "web developer"},
    "Backend": {"backend", "back-end", "back end", "api developer", "server"},
    "Machine Learning": {
        "ai", "ml", "machine learning", "artificial intelligence", "ai engineer",
        "ml engineer", "data scientist", "deep learning",
    },
    "Data": {"data engineer", "data analyst", "analytics"},
    "Mobile": {"mobile", "ios developer", "android developer", "app developer"},
}
_CATEGORY_GAP_ACTIONS: dict[str, str] = {
    "Machine Learning": "Build one end-to-end AI project using RAG or LangGraph.",
    "Frontend": "Build one polished, deployed frontend project with real users or design-partner feedback.",
    "Backend": "Build one backend service with real infrastructure concerns — auth, a database, and deployment.",
    "Data": "Build one data project with a real pipeline: ingestion, cleaning, and a dashboard or model.",
    "Mobile": "Ship one mobile app to the App Store or Play Store, even a small one.",
}
_LEADERSHIP_GOAL_HINTS = ("lead", "leadership", "manager", "management", "founder")
_RESEARCH_GOAL_HINTS = ("research", "phd", "scientist", "academia")

# ---- missing signals -------------------------------------------------------

_MISSING_SIGNAL_LIBRARY: dict[str, dict] = {
    "No Open Source": {
        "importance": "high",
        "why_it_matters": "Recruiters weight verifiable, public code more heavily than "
        "self-reported skills — without it, technical claims are unverifiable.",
        "recommended_action": "Publish your strongest project on GitHub and pin it to your profile.",
        "roi_impact": "Makes your technical depth verifiable instead of self-reported.",
        "score_gain": 7,
        "affected_opportunities": ["Software engineering internships", "Any role that screens technical claims", "Open-source-first employers"],
    },
    "No Leadership": {
        "importance": "medium",
        "why_it_matters": "Programs and recruiters look for evidence of initiative beyond "
        "individual contribution, even in early-career candidates.",
        "recommended_action": "Take (or document) a lead role in a club, project team, or hackathon.",
        "roi_impact": "Signals initiative and ownership beyond individual contribution.",
        "score_gain": 5,
        "affected_opportunities": ["Leadership development programs", "Team-lead-track roles", "Fellowships weighing initiative"],
    },
    "No Hackathons": {
        "importance": "medium",
        "why_it_matters": "Hackathons are one of the fastest, most legible ways to show "
        "you can build under real constraints, not just complete coursework.",
        "recommended_action": "Enter one hackathon and ship something, even if it's rough.",
        "roi_impact": "Demonstrates shipping speed and teamwork under a deadline.",
        "score_gain": 6,
        "affected_opportunities": ["Early-career software roles", "Hackathon-sourced recruiting pipelines"],
    },
    "No Portfolio": {
        "importance": "high",
        "why_it_matters": "Without a resume or a public profile of work, a recruiter has "
        "nothing to review before a screening call.",
        "recommended_action": "Upload a resume and add a portfolio link (GitHub or a personal site).",
        "roi_impact": "Gives recruiters something concrete to review before a screen.",
        "score_gain": 8,
        "affected_opportunities": ["Any role with a resume-screen stage", "Referral-based applications"],
    },
    "No Research": {
        "importance": "low",
        "why_it_matters": "For research-oriented tracks specifically, published or "
        "supervised work is the strongest available signal.",
        "recommended_action": "Reach out to a professor or lab for a research assistant role.",
        "roi_impact": "Strengthens candidacy specifically for research-track programs.",
        "score_gain": 4,
        "affected_opportunities": ["Research fellowships", "Graduate research assistantships", "PhD-track programs"],
    },
}


# ---- recruiter signals: observable, not verified -------------------------
#
# Deliberately makes no verification claim — this platform never checks the
# actual contents of a GitHub repo, a resume file, or a LinkedIn profile.
# Every status below is derived only from what's observable in the profile's
# own stated fields (a link exists, an experience is logged, a skill is
# listed), and "Unknown" is used rather than guessing when the profile
# genuinely doesn't contain enough information to judge a signal — see
# RecruiterSignal's docstring in schemas/analysis.py. why_it_matters and
# recommended_action are fixed per signal (they describe why recruiters
# generally care about this category and what generally closes the gap, not
# something inferred per-user), matching how a recruiter would explain their
# own checklist.
_RECRUITER_SIGNAL_LIBRARY: dict[str, dict] = {
    "Technical Experience": {
        "why_it_matters": "Recruiters check for direct evidence of applying technical skills in real "
        "settings, not just a list of tools.",
        "recommended_action": "Log a specific project or role with concrete technical details and outcomes.",
    },
    "Public Portfolio": {
        "why_it_matters": "Recruiters often look for public work to understand how candidates apply "
        "their skills beyond coursework.",
        "recommended_action": "Publish one end-to-end project on GitHub and link it to your profile.",
    },
    "Industry Exposure": {
        "why_it_matters": "Real-world work experience (internships, jobs) signals readiness for a "
        "professional environment in a way coursework alone does not.",
        "recommended_action": "Pursue an internship or part-time role, even a short one, in your target field.",
    },
    "Leadership": {
        "why_it_matters": "Recruiters look for evidence of ownership and initiative beyond individual "
        "contribution, even in early-career candidates.",
        "recommended_action": "Take or document a lead role in a club, project team, or hackathon.",
    },
    "AI/ML Focus": {
        "why_it_matters": "For AI/ML-oriented roles specifically, recruiters check for hands-on work "
        "with real models or data, not just stated interest.",
        "recommended_action": "Build one project that trains or fine-tunes a model on a real dataset.",
    },
    "Open Source": {
        "why_it_matters": "Public, reviewable code lets recruiters see how a candidate actually writes "
        "software, not just what they claim to know.",
        "recommended_action": "Make one existing project's repository public, or contribute to an "
        "existing open-source project.",
    },
    "Community Involvement": {
        "why_it_matters": "Recruiters read community activity (hackathons, meetups, organizing) as a "
        "sign of engagement beyond required coursework or work.",
        "recommended_action": "Enter one hackathon or help organize a club event.",
    },
    "Research Experience": {
        "why_it_matters": "For research-track roles and programs, supervised or published work is the "
        "strongest available signal.",
        "recommended_action": "Reach out to a professor or lab for a research assistant role, even part-time.",
    },
    "Communication": {
        "why_it_matters": "A clearly written bio and project descriptions are often a recruiter's first "
        "read on how a candidate will communicate on the job.",
        "recommended_action": "Write a specific bio and a detailed description for each logged experience.",
    },
    "Professional Presence": {
        "why_it_matters": "A complete, linked profile (resume, LinkedIn, a clear headline) is what makes "
        "a candidate easy for a recruiter to act on after an initial review.",
        "recommended_action": "Add a resume and a LinkedIn link, and fill in a clear headline.",
    },
}


class MockAnalysisGenerator(BaseAnalysisGenerator):
    name = "mock-v1"

    async def generate(self, context: ProfileContext) -> AnalysisContent:
        career_signals = self._career_signals(context)
        missing_signals = self._missing_signals(context)
        profile_contradictions = self._profile_contradictions(context)
        recruiter_signals = self._recruiter_signals(context)
        highest_roi = self._highest_roi(missing_signals)
        profile_diagnosis = self._profile_diagnosis(
            context, career_signals, missing_signals, recruiter_signals
        )

        content = AnalysisContent(
            # A placeholder — utils.scoring.reconcile() (called below, and
            # identically by every generator) recomputes this from scratch as
            # an itemized sum, never trusting this number.
            overall_score=50,
            profile_diagnosis=profile_diagnosis,
            career_signals=career_signals,
            missing_signals=missing_signals,
            profile_contradictions=profile_contradictions,
            score_breakdown=ScoreBreakdown(base_score=0, positive_factors=[], negative_factors=[], final_score=0),
            growth_simulation=GrowthSimulation(current_score=0, future_score=0, actions=[], calculation_basis=""),
            recruiter_signals=recruiter_signals,
            highest_roi_recommendation=highest_roi,
        )
        return reconcile(content)

    # ---- career signals ------------------------------------------------------

    def _career_signals(self, context: ProfileContext) -> list[CareerSignal]:
        skills_lower = {s.lower() for s in context.all_skills}
        experience_text = " ".join(
            f"{e.get('title') or ''} {e.get('description') or ''}" for e in context.experiences
        ).lower()
        n_experiences = len(context.experiences)
        signals: list[CareerSignal] = []

        # 1. Technical Leadership — leadership signal AND technical substance,
        # not either alone (a club president with no technical work isn't
        # technical leadership; a solo IC with no ownership role isn't either).
        technical_hits = skills_lower & (_TECHNICAL_DEPTH_SKILLS | _BUILDER_SKILLS)
        confidence = 15
        evidence = []
        if context.has_leadership_signal:
            confidence += 35
            evidence.append("Leadership language found in experience history or interests")
        if technical_hits:
            confidence += min(30, len(technical_hits) * 8)
            evidence.append(f"Technical skill(s) present alongside that context: {', '.join(sorted(technical_hits))}")
        confidence = min(95, confidence)
        signals.append(
            CareerSignal(
                signal="Technical Leadership",
                strength=_strength_for(confidence),
                confidence=confidence,
                evidence=evidence or ["No leadership role combined with technical work found yet"],
                interpretation=(
                    "Has combined ownership of people or outcomes with hands-on technical work, "
                    "not just one or the other."
                    if context.has_leadership_signal and technical_hits
                    else "Either the leadership context or the technical substance behind it is "
                    "missing — this profile shows one, not both, or neither."
                ),
            )
        )

        # 2. Product Building — user/product-facing framing plus evidence of
        # actually shipping things (builder skills, logged experiences).
        product_hits = sum(1 for hint in _PRODUCT_HINTS if hint in experience_text)
        builder_hits = skills_lower & _BUILDER_SKILLS
        confidence = 15 + product_hits * 15 + (15 if builder_hits else 0) + min(20, n_experiences * 8)
        confidence = min(95, confidence)
        signals.append(
            CareerSignal(
                signal="Product Building",
                strength=_strength_for(confidence),
                confidence=confidence,
                evidence=[
                    f"{product_hits} product/user-oriented reference(s) in logged experience",
                    f"{n_experiences} logged experience(s) built with tools like "
                    f"{', '.join(sorted(builder_hits)) or 'an unspecified stack'}",
                ],
                interpretation=(
                    "Shows evidence of building things with a user or outcome in mind, not just "
                    "technical execution in isolation."
                    if product_hits and n_experiences
                    else "Limited evidence connecting what was built to a user or business outcome — "
                    "descriptions read as technical tasks rather than product decisions."
                ),
            )
        )

        # 3. Research Exposure
        confidence = 75 if context.has_research_signal else 18
        signals.append(
            CareerSignal(
                signal="Research Exposure",
                strength=_strength_for(confidence),
                confidence=confidence,
                evidence=[
                    "Research-oriented interest or experience found"
                    if context.has_research_signal
                    else "No lab work, papers, or research interests found in the profile"
                ],
                interpretation=(
                    "Has direct exposure to open-ended, research-style work rather than only "
                    "well-defined coursework or product tasks."
                    if context.has_research_signal
                    else "No research-track evidence in the profile — this is a genuine absence, "
                    "not a weak signal, if research-track roles are a goal."
                ),
            )
        )

        # 4. Community Involvement
        community_hits = sum(1 for hint in _COMMUNITY_HINTS if hint in experience_text)
        confidence = (
            15
            + community_hits * 20
            + (20 if context.has_hackathon_signal else 0)
            + (20 if context.has_open_source_signal else 0)
        )
        confidence = min(95, confidence)
        signals.append(
            CareerSignal(
                signal="Community Involvement",
                strength=_strength_for(confidence),
                confidence=confidence,
                evidence=[
                    f"Hackathon participation: {'yes' if context.has_hackathon_signal else 'no'}",
                    f"Open source contribution: {'yes' if context.has_open_source_signal else 'no'}",
                    f"{community_hits} community/mentorship reference(s) in logged experience",
                ],
                interpretation=(
                    "Contributes beyond individual work — hackathons, open source, or organizing others."
                    if confidence >= 45
                    else "No community-facing activity found yet — all logged work reads as "
                    "individual contribution."
                ),
            )
        )

        # 5. Learning Consistency — breadth across skill areas plus a
        # track record of more than one logged engagement over time.
        buckets_touched = sum(1 for bucket in _SKILL_CATEGORY_BUCKETS.values() if skills_lower & bucket)
        confidence = 15 + buckets_touched * 15 + min(30, n_experiences * 10)
        confidence = min(95, confidence)
        signals.append(
            CareerSignal(
                signal="Learning Consistency",
                strength=_strength_for(confidence),
                confidence=confidence,
                evidence=[
                    f"Skills span {buckets_touched} of {len(_SKILL_CATEGORY_BUCKETS)} tracked area(s)",
                    f"{n_experiences} logged experience(s) over time",
                ],
                interpretation=(
                    f"Has kept picking up new areas across {n_experiences} engagement(s) rather than "
                    f"stopping after one."
                    if buckets_touched >= 2 and n_experiences >= 2
                    else "Not enough logged history yet to distinguish steady, ongoing learning from "
                    "a single burst of activity."
                ),
            )
        )

        # 6. Software Engineering Foundation — core CS fundamentals plus
        # hands-on tooling, the base layer every technical role checks for.
        foundation_hits = skills_lower & (_TECHNICAL_DEPTH_SKILLS | _BUILDER_SKILLS | {"git", "sql"})
        confidence = 20 + len(foundation_hits) * 9 + min(25, n_experiences * 10)
        confidence = min(95, confidence)
        signals.append(
            CareerSignal(
                signal="Software Engineering Foundation",
                strength=_strength_for(confidence),
                confidence=confidence,
                evidence=[
                    f"Foundational skill(s) on file: {', '.join(sorted(foundation_hits)) or 'none listed'}",
                    f"{n_experiences} logged experience(s) applying them",
                ],
                interpretation=(
                    "Has the baseline technical fundamentals most engineering screens check for."
                    if len(foundation_hits) >= 2
                    else "Skills on file lean toward high-level tools rather than core fundamentals "
                    "(algorithms, data structures, system design) — this is the most common early "
                    "screening gap."
                ),
            )
        )

        return signals

    # ---- missing signals ----------------------------------------------------

    def _missing_signals(self, context: ProfileContext) -> list[MissingSignal]:
        checks = [
            ("No Open Source", context.has_open_source_signal),
            ("No Leadership", context.has_leadership_signal),
            ("No Hackathons", context.has_hackathon_signal),
            ("No Portfolio", context.has_portfolio_signal),
            ("No Research", context.has_research_signal),
        ]
        signals = []
        for title, present in checks:
            if present:
                continue
            info = _MISSING_SIGNAL_LIBRARY[title]
            signals.append(
                MissingSignal(
                    title=title,
                    importance=info["importance"],
                    why_it_matters=info["why_it_matters"],
                    expected_score_impact=info["score_gain"],
                    affected_opportunities=info["affected_opportunities"],
                    recommended_action=info["recommended_action"],
                )
            )
        return signals

    # ---- profile contradictions ----------------------------------------------

    def _category_of(self, text: str) -> str | None:
        lowered = text.lower()
        best_category, best_hits = None, 0
        for category, keywords in _CATEGORY_KEYWORDS.items():
            hits = sum(1 for kw in keywords if kw in lowered)
            if hits > best_hits:
                best_category, best_hits = category, hits
        return best_category

    def _target_category(self, context: ProfileContext) -> str | None:
        haystack = f"{context.profile.get('target_role') or ''} {' '.join(context.career_interests)}".lower()
        if not haystack.strip():
            return None
        for category, aliases in _CATEGORY_ALIASES.items():
            if any(alias in haystack for alias in aliases):
                return category
        return None

    def _profile_contradictions(self, context: ProfileContext) -> list[ProfileContradiction]:
        contradictions: list[ProfileContradiction] = []
        goal_text = f"{context.profile.get('target_role') or ''} {' '.join(context.career_interests)}".lower()

        # 1. Stated target direction vs. dominant logged effort category.
        target = self._target_category(context)
        if target is not None and context.experiences:
            counts: dict[str, int] = {}
            for experience in context.experiences:
                text = (
                    f"{experience.get('title') or ''} {experience.get('description') or ''} "
                    f"{' '.join(experience.get('skills_used') or [])}"
                )
                category = self._category_of(text)
                if category:
                    counts[category] = counts.get(category, 0) + 1

            if counts:
                dominant, dominant_count = max(counts.items(), key=lambda pair: pair[1])
                target_count = counts.get(target, 0)
                if dominant != target and dominant_count >= 2 and target_count < dominant_count:
                    target_role_text = context.profile.get("target_role") or f"a {target} role"
                    contradictions.append(
                        ProfileContradiction(
                            contradiction=(
                                f"States {target_role_text} as the target, but most logged effort is "
                                f"{dominant} work"
                            ),
                            stated_goal=target_role_text,
                            observed_evidence=[
                                f"{dominant_count} {dominant} project(s)",
                                f"{target_count} {target} project(s)",
                            ],
                            why_it_matters=(
                                f"Recruiters may read this profile as {dominant}-focused rather than "
                                f"{target}-focused, regardless of the stated target role."
                            ),
                            how_to_close_gap=_CATEGORY_GAP_ACTIONS.get(
                                target, f"Build one project squarely in {target} to balance out the portfolio."
                            ),
                        )
                    )

        # 2. Stated interest in leadership vs. no leadership evidence.
        if any(hint in goal_text for hint in _LEADERSHIP_GOAL_HINTS) and not context.has_leadership_signal:
            contradictions.append(
                ProfileContradiction(
                    contradiction="Lists a leadership-oriented goal, but no logged experience carries a leadership-scoped role",
                    stated_goal=context.profile.get("target_role") or "a leadership-oriented interest",
                    observed_evidence=["No leadership titles or language found in any logged experience"],
                    why_it_matters=(
                        "A stated leadership interest with zero supporting experience reads as "
                        "aspirational rather than demonstrated — recruiters weight the evidence, not "
                        "the stated interest."
                    ),
                    how_to_close_gap="Take or document a lead role in a club, project team, or hackathon.",
                )
            )

        # 3. Stated research/academic direction vs. no research evidence.
        if any(hint in goal_text for hint in _RESEARCH_GOAL_HINTS) and not context.has_research_signal:
            contradictions.append(
                ProfileContradiction(
                    contradiction="Lists a research or academic goal, but no logged experience shows research-style work",
                    stated_goal=context.profile.get("target_role") or "a research-oriented interest",
                    observed_evidence=["No lab work, papers, or research-scoped experience found"],
                    why_it_matters=(
                        "Research-track programs weight supervised or published work heavily — a "
                        "stated interest alone does not substitute for it."
                    ),
                    how_to_close_gap="Reach out to a professor or lab for a research assistant role, even part-time.",
                )
            )

        return contradictions[:3]

    # ---- recruiter signals -----------------------------------------------------

    def _signal(self, name: str, status: str) -> RecruiterSignal:
        info = _RECRUITER_SIGNAL_LIBRARY[name]
        return RecruiterSignal(
            signal=name,
            status=status,
            why_it_matters=info["why_it_matters"],
            recommended_action=info["recommended_action"],
        )

    def _recruiter_signals(self, context: ProfileContext) -> list[RecruiterSignal]:
        skills_lower = {s.lower() for s in context.all_skills}
        n_experiences = len(context.experiences)
        bio = (context.profile.get("bio") or "").strip()
        headline = (context.profile.get("headline") or "").strip()
        has_linkedin = bool(context.profile.get("linkedin_url"))
        experience_text = " ".join(
            f"{e.get('title') or ''} {e.get('description') or ''}" for e in context.experiences
        ).lower()

        signals: list[RecruiterSignal] = []

        # Technical Experience
        technical_hits = skills_lower & (_TECHNICAL_DEPTH_SKILLS | _BUILDER_SKILLS)
        if n_experiences >= 2 and technical_hits:
            status = "Strong"
        elif n_experiences >= 1 or technical_hits:
            status = "Moderate"
        elif skills_lower:
            status = "Limited"
        else:
            status = "Missing"
        signals.append(self._signal("Technical Experience", status))

        # Public Portfolio — presence of a linked profile, never a claim
        # about what's actually in it.
        if context.has_github and context.has_resume:
            status = "Strong"
        elif context.has_github or context.has_resume:
            status = "Moderate"
        else:
            status = "Missing"
        signals.append(self._signal("Public Portfolio", status))

        # Industry Exposure
        real_world_types = {"internship", "full_time", "part_time", "job", "co_op"}
        real_world = sum(
            1 for e in context.experiences if (e.get("experience_type") or "").lower() in real_world_types
        )
        if real_world >= 2:
            status = "Strong"
        elif real_world == 1:
            status = "Moderate"
        elif n_experiences > 0:
            status = "Limited"
        else:
            status = "Missing"
        signals.append(self._signal("Industry Exposure", status))

        # Leadership
        if context.has_leadership_signal:
            status = "Strong" if n_experiences >= 2 else "Moderate"
        else:
            status = "Missing"
        signals.append(self._signal("Leadership", status))

        # AI/ML Focus
        ml_skill_hits = skills_lower & {
            "machine learning", "ml", "ai", "tensorflow", "pytorch", "nlp",
            "deep learning", "data science", "llm", "langchain", "langgraph",
        }
        ml_hints = ("machine learning", "ml ", " ml", "ai", "nlp", "deep learning", "langchain", "langgraph")
        ml_experience = any(hint in experience_text for hint in ml_hints)
        ml_interest = any(
            "machine learning" in interest.lower() or "ai" in interest.lower()
            for interest in context.career_interests
        )
        if ml_skill_hits and ml_experience:
            status = "Strong"
        elif ml_skill_hits or ml_experience:
            status = "Moderate"
        elif ml_interest:
            status = "Limited"
        else:
            status = "Missing"
        signals.append(self._signal("AI/ML Focus", status))

        # Open Source — a link plus an explicit open-source signal is
        # "Strong"; a link alone is "Moderate" (present, but not confirmed to
        # be open-source contribution specifically) since this platform does
        # not inspect what's actually in the linked account.
        if context.has_open_source_signal:
            status = "Strong"
        elif context.has_github:
            status = "Moderate"
        else:
            status = "Missing"
        signals.append(self._signal("Open Source", status))

        # Community Involvement
        community_hits = sum(1 for hint in _COMMUNITY_HINTS if hint in experience_text)
        if community_hits >= 2 or (community_hits and context.has_hackathon_signal):
            status = "Strong"
        elif community_hits or context.has_hackathon_signal:
            status = "Moderate"
        else:
            status = "Missing"
        signals.append(self._signal("Community Involvement", status))

        # Research Experience
        if context.has_research_signal:
            research_titled = any("research" in (e.get("title") or "").lower() for e in context.experiences)
            status = "Strong" if research_titled else "Moderate"
        else:
            status = "Missing"
        signals.append(self._signal("Research Experience", status))

        # Communication — deliberately conservative. There is no reliable way
        # to judge communication ability from structured profile fields, so
        # this stays at "Unknown" unless there's enough self-authored text to
        # say anything at all, and never claims "Strong"/"Missing" outright.
        described_experiences = sum(1 for e in context.experiences if (e.get("description") or "").strip())
        if not bio and described_experiences == 0:
            status = "Unknown"
        elif len(bio) >= 80 and described_experiences >= 1:
            status = "Strong"
        elif bio or described_experiences:
            status = "Moderate"
        else:
            status = "Unknown"
        signals.append(self._signal("Communication", status))

        # Professional Presence
        present_count = sum([bool(headline), context.has_resume, has_linkedin])
        if present_count == 3:
            status = "Strong"
        elif present_count == 2:
            status = "Moderate"
        elif present_count == 1:
            status = "Limited"
        else:
            status = "Missing"
        signals.append(self._signal("Professional Presence", status))

        return signals

    # ---- profile diagnosis ----------------------------------------------------

    def _profile_diagnosis(
        self,
        context: ProfileContext,
        career_signals: list[CareerSignal],
        missing_signals: list[MissingSignal],
        recruiter_signals: list[RecruiterSignal],
    ) -> ProfileDiagnosis:
        observed = [s for s in career_signals if s.strength != "not observed"]
        strongest = max(observed, key=lambda s: s.confidence) if observed else None

        importance_rank = {"high": 0, "medium": 1, "low": 2}
        ranked_missing = sorted(missing_signals, key=lambda s: importance_rank[s.importance])
        top_gap = ranked_missing[0] if ranked_missing else None

        if strongest:
            strongest_signal = strongest.signal
            strongest_signal_evidence = strongest.evidence
        else:
            strongest_signal = "No strong signal detected yet"
            strongest_signal_evidence = [
                "Profile currently has too little logged experience or skill data to support a "
                "confident signal in any direction"
            ]

        weak_statuses = {"Missing", "Limited"}
        status_rank = {"Missing": 0, "Limited": 1, "Unknown": 2, "Moderate": 3, "Strong": 4}
        weakest_recruiter_signal = (
            min(
                (s for s in recruiter_signals if s.status in weak_statuses),
                key=lambda s: status_rank[s.status],
            )
            if any(s.status in weak_statuses for s in recruiter_signals)
            else None
        )

        if top_gap:
            limiting_factor = top_gap.title.replace("No ", "Little to no ")
            limiting_factor_evidence = [top_gap.why_it_matters]
        elif weakest_recruiter_signal:
            limiting_factor = f"{weakest_recruiter_signal.signal} ({weakest_recruiter_signal.status.lower()})"
            limiting_factor_evidence = [weakest_recruiter_signal.why_it_matters]
        else:
            limiting_factor = "Overall evidence depth"
            limiting_factor_evidence = ["Profile has very little logged experience or skill data on file yet"]

        if top_gap:
            highest_impact_area = top_gap.title.replace("No ", "Adding ")
            highest_impact_reason = (
                f"This is the highest-importance gap detected, expected to move the score by "
                f"roughly {top_gap.expected_score_impact} points once addressed."
            )
        else:
            highest_impact_area = "Adding more logged experience"
            highest_impact_reason = (
                "No specific gap stands out — the fastest remaining way to raise the score is "
                "adding more verifiable projects and experience, since the profile has no single "
                "dominant weakness left to close."
            )

        skill_count = len(context.all_skills)
        experience_count = len(context.experiences)
        summary = (
            f"{context.full_name} presents {'a well-rounded' if skill_count >= 6 and experience_count >= 2 else 'an early-stage'} "
            f"technical profile with {skill_count} listed skill(s) and {experience_count} logged "
            f"experience(s). The strongest observable pattern is {strongest_signal.lower() if strongest else 'not yet established'}"
            f"{', supported by ' + '; '.join(strongest_signal_evidence[:2]) if strongest and strongest_signal_evidence else ''}. "
            f"The most limiting factor right now is {limiting_factor.lower()}, which is the first thing "
            f"a recruiter or automated match is likely to notice as missing. Addressing "
            f"{highest_impact_area.lower()} is the single highest-leverage next step, since it targets "
            f"the largest currently-open gap rather than a marginal improvement elsewhere."
        )

        return ProfileDiagnosis(
            strongest_signal=strongest_signal,
            strongest_signal_evidence=strongest_signal_evidence,
            limiting_factor=limiting_factor,
            limiting_factor_evidence=limiting_factor_evidence,
            highest_impact_area=highest_impact_area,
            highest_impact_reason=highest_impact_reason,
            summary=summary,
        )

    # ---- highest ROI recommendation -------------------------------------------

    def _highest_roi(self, missing: list[MissingSignal]) -> HighestRoiRecommendation:
        importance_rank = {"high": 0, "medium": 1, "low": 2}
        ranked = sorted(missing, key=lambda s: importance_rank[s.importance])
        if ranked:
            top = ranked[0]
            info = _MISSING_SIGNAL_LIBRARY[top.title]
            return HighestRoiRecommendation(
                title=top.recommended_action,
                evidence_gap=top.title.replace("No ", "No evidence of "),
                impact=info["roi_impact"],
                reason=top.why_it_matters,
                estimated_score_gain=top.expected_score_impact,
            )
        return HighestRoiRecommendation(
            title="Keep your profile current — add new projects and experiences as they happen.",
            evidence_gap="No specific evidence gap detected right now.",
            impact="Keeps recommendations accurate as your skill set and experience grow.",
            reason="Your profile currently has no major detected gaps.",
            estimated_score_gain=2,
        )
