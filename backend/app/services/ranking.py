"""Hybrid recommendation ranking.

Pure functions only — no Supabase/network I/O, nothing async — so this
whole module is unit-testable without mocking anything (see
tests/test_ranking.py). recommendation_service.py is the only caller: it
does the I/O (retrieval, hydration) and hands the results in here.
"""

import re
from datetime import datetime, timezone

from app.schemas.recommendation import MatchReason

# Centralized weights, per the product spec — tune here, nowhere else. Each
# value is this factor's share of the final [0, 1] score, so they must sum
# to 1.0 (enforced below at import time rather than left as a comment
# someone can silently invalidate).
RANKING_WEIGHTS: dict[str, float] = {
    "semantic": 0.45,
    "keyword": 0.25,
    "skill_overlap": 0.10,
    "career_interest_overlap": 0.10,
    "target_role_relevance": 0.05,
    "freshness": 0.05,
}

assert abs(sum(RANKING_WEIGHTS.values()) - 1.0) < 1e-9, "RANKING_WEIGHTS must sum to 1.0"

# Freshness decays linearly to 0 over this many days, then floors there —
# "a small boost" per spec, not something that can outrank real relevance:
# the 5% weight already caps its influence, this just keeps the boost
# meaningful within that 5% instead of an arbitrary/unbounded scale.
FRESHNESS_WINDOW_DAYS = 90

_WORD_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
# Any run of non-alphanumeric characters (hyphens, dots, underscores,
# slashes, ampersands, ...) collapses to a single space, so "Node.js",
# "node-js", "node_js" and "Node JS" all normalise to the same "node js" —
# the punctuation/separator variations skills and interests actually show
# up in, without a synonym dictionary (which wouldn't be deterministic to
# reason about the same way).
_SEPARATOR_RE = re.compile(r"[^a-z0-9]+")


def _words(text: str | None) -> list[str]:
    return _WORD_RE.findall((text or "").lower())


def _normalise_term(value: str) -> str:
    """Casing/whitespace/punctuation-insensitive form of one skill/interest
    term: lowercase, strip, collapse any run of non-alphanumeric characters
    to a single space. "  Node.js " / "node-js" / "NODE_JS" all become
    "node js"."""
    return _SEPARATOR_RE.sub(" ", value.strip().lower()).strip()


def _compact(value: str) -> str:
    """Space-free form of a normalised term, used as a secondary match so
    "nodejs" (no separator at all) still matches "node js" / "node.js" —
    common variations differ in whether a separator is present, not just
    which one."""
    return value.replace(" ", "")


def _normalise_terms(values: list[str] | None) -> list[str]:
    """Normalise + de-duplicate while preserving order. Empty/whitespace-
    only entries are dropped rather than kept as empty-string "terms" that
    could spuriously match each other."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values or []:
        term = _normalise_term(value or "")
        if term and term not in seen:
            seen.add(term)
            result.append(term)
    return result


def _term_matches(term: str, candidate_terms: set[str], candidate_compact: set[str]) -> bool:
    return term in candidate_terms or _compact(term) in candidate_compact


def build_keyword_query(profile: dict) -> str:
    """A `to_tsquery`-compatible OR expression ("word1 | word2 | ...")
    built from the profile's own meaningful fields.

    OR, not AND: this is a *retrieval* leg meant to maximize recall of
    candidates sharing ANY meaningful term with the profile — actual
    relevance weighting happens later in score_candidate(). websearch_to_
    tsquery's default AND-between-words behavior would instead require an
    opportunity to match every single skill/interest at once, which for a
    profile with more than one or two signals would return almost nothing.

    Priority order (per spec — target_role, current_skills, career_
    interests, target_company, headline) is reflected in the order terms
    are added, so earlier fields survive the 40-term cap first; OR-matching
    means every field still contributes to whether a candidate is
    retrieved at all, not just how prominently. True per-field ranking
    weight beyond that would need setweight('A'..'D') on the search_vector
    column itself, which lives in a trigger this module doesn't own — see
    the note on RecommendationRepository.keyword_candidates().

    Words are extracted with `[a-z0-9]+` (so "Node.js" -> "node", "js"),
    which also means every token handed to to_tsquery is alphanumeric-only
    — there's no tsquery syntax (&, |, !, parens) a profile field could
    ever inject.
    """
    ordered_fields = [
        profile.get("target_role"),
        *(profile.get("current_skills") or []),
        *(profile.get("career_interests") or []),
        profile.get("target_company"),
        profile.get("headline"),
    ]

    seen: set[str] = set()
    terms: list[str] = []
    for field in ordered_fields:
        for word in _words(field):
            if word not in seen:
                seen.add(word)
                terms.append(word)

    return " | ".join(terms[:40])


def skill_overlap_score(
    current_skills: list[str], opportunity_tags: list[str]
) -> tuple[float, list[str]]:
    """profiles.current_skills vs. opportunities.tags. Both sides go through
    _normalise_terms(), so matching is robust to casing ("Python" ==
    "python"), whitespace ("  React " == "React"), and punctuation/
    separator variations ("Node.js" == "node-js" == "Node JS" == "nodejs").
    """
    skills = _normalise_terms(current_skills)
    if not skills:
        return 0.0, []
    tags = set(_normalise_terms(opportunity_tags))
    tags_compact = {_compact(tag) for tag in tags}
    matched = [skill for skill in skills if _term_matches(skill, tags, tags_compact)]
    return len(matched) / len(skills), matched


def career_interest_overlap_score(
    career_interests: list[str], opportunity_tags: list[str], opportunity_text: str
) -> tuple[float, list[str]]:
    """profiles.career_interests vs. opportunities.tags AND relevant
    opportunity text (title + description) — an interest can be reflected
    in the free text even when it isn't literally one of the tags. Same
    casing/whitespace/punctuation-insensitive matching as skill_overlap_
    score for the tags comparison; the free-text fallback splits the
    normalised interest into words and requires all of them to appear
    somewhere in the text (so "machine learning" matches text containing
    both "machine" and "learning", not just one of them).
    """
    interests = _normalise_terms(career_interests)
    if not interests:
        return 0.0, []
    tags = set(_normalise_terms(opportunity_tags))
    tags_compact = {_compact(tag) for tag in tags}
    text_words = set(_words(opportunity_text))

    matched = [
        interest
        for interest in interests
        if _term_matches(interest, tags, tags_compact)
        or all(word in text_words for word in interest.split())
    ]
    return len(matched) / len(interests), matched


def target_role_relevance_score(
    target_role: str | None,
    title: str | None,
    tags: list[str],
    description: str | None,
    organization: str | None = None,
) -> float:
    """profiles.target_role vs. title/tags/organization/description — a
    soft relevance signal, never a filter (spec: "Do not hard-filter based
    on target role"). Tiered by how strong a signal each field is: a role
    showing up in an opportunity's own title is the strongest signal: tags
    are curated categorization so a match there is deliberate too, then the
    organization's own name, then merely appearing somewhere in the free-
    text description is the weakest (most incidental) signal. Matching
    against `organization` is an "and" addition to the four fields already
    compared, not a replacement for any of them — a role word coincidentally
    appearing in a company's name (e.g. "Engineer" in "Persevere
    Engineering") is real but weaker signal than that same word being the
    opportunity's actual title.
    """
    role_words = set(_words(target_role))
    if not role_words:
        return 0.0

    title_words = set(_words(title))
    tag_words = set(_words(" ".join(tags or [])))
    organization_words = set(_words(organization))
    description_words = set(_words(description))

    if role_words & title_words:
        return 1.0
    if role_words & tag_words:
        return 0.7
    if role_words & organization_words:
        return 0.5
    if role_words & description_words:
        return 0.4
    return 0.0


def freshness_score(posted_at: datetime | str | None, *, now: datetime | None = None) -> float:
    """Linear decay from 1.0 (posted today) to 0.0 (posted
    FRESHNESS_WINDOW_DAYS+ ago). A small boost, not a filter — an old
    listing scores 0 on this one component but can still rank highly on
    the strength of the other five.

    Accepts a string too: PostgREST/supabase-py return timestamptz columns
    as ISO-8601 strings, and hydrate_opportunities() in
    recommendation_repository.py hands rows straight through as plain
    dicts rather than parsing every timestamp field up front.
    """
    if posted_at is None:
        return 0.0
    if isinstance(posted_at, str):
        try:
            posted_at = datetime.fromisoformat(posted_at)
        except ValueError:
            return 0.0
    now = now or datetime.now(tz=timezone.utc)
    if posted_at.tzinfo is None:
        posted_at = posted_at.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (now - posted_at).total_seconds() / 86400)
    return max(0.0, 1.0 - age_days / FRESHNESS_WINDOW_DAYS)


def normalise_leg_scores(raw: dict[str, float]) -> dict[str, float]:
    """Min-max normalize a retrieval leg's raw scores into [0, 1] *within
    this candidate batch*. Needed for the keyword leg: ts_rank's scale is
    arbitrary (depends on document length/term frequency, not bounded to
    [0, 1] the way cosine similarity already effectively is), so it isn't
    safe to feed directly into a weighted blend with the other [0, 1]
    components without first putting it on the same scale.
    """
    if not raw:
        return {}
    values = raw.values()
    lo, hi = min(values), max(values)
    if hi - lo < 1e-9:
        # Every candidate scored identically (e.g. a single-result batch) —
        # treat as "all equally relevant" rather than dividing by ~0.
        return dict.fromkeys(raw, 1.0)
    return {key: (value - lo) / (hi - lo) for key, value in raw.items()}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def score_candidate(
    *,
    opportunity: dict,
    profile: dict,
    semantic_similarity: float,
    keyword_relevance: float,
    now: datetime | None = None,
) -> tuple[float, list[MatchReason]]:
    """Blend all six weighted components for one opportunity.

    `semantic_similarity` and `keyword_relevance` must already be [0, 1]
    (see RecommendationRepository for the former, normalise_leg_scores()
    above for the latter) — this function is pure and doesn't know how
    they got that way, it just clamps defensively.
    """
    skill_score, matched_skills = skill_overlap_score(
        profile.get("current_skills") or [], opportunity.get("tags") or []
    )
    interest_score, matched_interests = career_interest_overlap_score(
        profile.get("career_interests") or [],
        opportunity.get("tags") or [],
        f"{opportunity.get('title') or ''} {opportunity.get('description') or ''}",
    )
    role_score = target_role_relevance_score(
        profile.get("target_role"),
        opportunity.get("title"),
        opportunity.get("tags") or [],
        opportunity.get("description"),
        opportunity.get("organization"),
    )
    fresh_score = freshness_score(opportunity.get("posted_at"), now=now)

    components = {
        "semantic": _clamp01(semantic_similarity),
        "keyword": _clamp01(keyword_relevance),
        "skill_overlap": skill_score,
        "career_interest_overlap": interest_score,
        "target_role_relevance": role_score,
        "freshness": fresh_score,
    }

    total = sum(components[factor] * weight for factor, weight in RANKING_WEIGHTS.items())

    return _clamp01(total), _build_reasons(components, matched_skills, matched_interests)


def _build_reasons(
    components: dict[str, float], matched_skills: list[str], matched_interests: list[str]
) -> list[MatchReason]:
    reasons: list[MatchReason] = []

    if components["semantic"] > 0:
        reasons.append(
            MatchReason(
                factor="semantic",
                weight=RANKING_WEIGHTS["semantic"],
                detail=(
                    f"{round(components['semantic'] * 100)}% semantically "
                    "similar to your profile"
                ),
            )
        )
    if components["keyword"] > 0:
        reasons.append(
            MatchReason(
                factor="keyword",
                weight=RANKING_WEIGHTS["keyword"],
                detail="Matches keywords from your profile",
            )
        )
    if matched_skills:
        reasons.append(
            MatchReason(
                factor="skill_overlap",
                weight=RANKING_WEIGHTS["skill_overlap"],
                detail=(
                    f"Matches {len(matched_skills)} of your skills: "
                    f"{', '.join(matched_skills[:5])}"
                ),
            )
        )
    if matched_interests:
        reasons.append(
            MatchReason(
                factor="career_interest_overlap",
                weight=RANKING_WEIGHTS["career_interest_overlap"],
                detail=f"Aligned with your interest in {', '.join(matched_interests[:3])}",
            )
        )
    if components["target_role_relevance"] > 0:
        reasons.append(
            MatchReason(
                factor="target_role_relevance",
                weight=RANKING_WEIGHTS["target_role_relevance"],
                detail="Related to your target role",
            )
        )
    if components["freshness"] > 0.5:
        reasons.append(
            MatchReason(
                factor="freshness",
                weight=RANKING_WEIGHTS["freshness"],
                detail="Recently posted",
            )
        )

    return reasons


def merge_candidate_ids(
    semantic: list[dict], keyword: list[dict]
) -> tuple[dict[str, float], dict[str, float]]:
    """Two raw-score maps (opportunity_id -> score), one per leg — the
    union of their keys is every unique candidate headed into ranking.
    Kept as two maps rather than flattened into one merged/deduplicated
    list, per spec: "Keep both semantic and keyword scores" — an
    opportunity in both legs should contribute both signals to its score,
    not just whichever leg happened to be merged in first.
    """
    semantic_by_id = {row["opportunity_id"]: row["similarity"] for row in semantic}
    keyword_by_id = {row["opportunity_id"]: row["rank"] for row in keyword}
    return semantic_by_id, keyword_by_id


def rank_candidates(
    *,
    opportunities: dict[str, dict],
    profile: dict,
    semantic_by_id: dict[str, float],
    keyword_by_id: dict[str, float],
    now: datetime | None = None,
) -> list[tuple[str, float, list[MatchReason]]]:
    """Score every candidate id and return (opportunity_id, score, reasons)
    sorted highest-first.

    `opportunities` is the hydrated id -> row map. An id present in
    semantic_by_id/keyword_by_id but missing from `opportunities` (e.g. an
    opportunity deactivated in the moment between retrieval and hydration)
    is silently skipped rather than raising — an expected race, not a bug.

    Deterministic by construction, including ties: candidate ids are
    collected into an order-preserving list (not a bare `set`, whose
    iteration order is hash-randomized per process in CPython — two
    candidates scoring identically could otherwise come back in a different
    relative order on every run/request), and the final sort breaks ties by
    opportunity_id rather than leaving them at whatever order they happened
    to be scored in.
    """
    keyword_normalised = normalise_leg_scores(keyword_by_id)
    # dict.fromkeys(...) both de-duplicates and preserves first-seen order —
    # semantic candidates first, then any keyword-only candidates appended
    # after. The actual ranking below doesn't depend on this order (it's a
    # full sort by score), but keeping it deterministic here means a
    # candidate's position among same-scored peers can't drift between
    # requests just because of set-iteration order.
    candidate_ids = list(dict.fromkeys([*semantic_by_id, *keyword_by_id]))

    scored: list[tuple[str, float, list[MatchReason]]] = []
    for opportunity_id in candidate_ids:
        opportunity = opportunities.get(opportunity_id)
        if opportunity is None:
            continue
        score, reasons = score_candidate(
            opportunity=opportunity,
            profile=profile,
            semantic_similarity=semantic_by_id.get(opportunity_id, 0.0),
            keyword_relevance=keyword_normalised.get(opportunity_id, 0.0),
            now=now,
        )
        scored.append((opportunity_id, score, reasons))

    # Ties broken by opportunity_id (ascending) rather than left to
    # insertion order, which is what actually guarantees the same input
    # always produces the same output ordering.
    scored.sort(key=lambda row: (-row[1], row[0]))
    return scored
