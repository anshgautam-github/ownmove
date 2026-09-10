"""Exercises `app.services.ranking` — pure functions, no Supabase/network
I/O, so every case here runs against plain dicts/lists with nothing mocked.

Covers: the weighted blend matches the product spec exactly (45/25/10/10/
5/5, summing to 1.0); the keyword query is OR-joined (not AND); skill/
interest/role matching is robust to casing, whitespace, and punctuation/
separator variation ("Node.js" == "node-js" == "NODE_JS" == "nodejs");
freshness decays gradually rather than abruptly excluding older listings;
merge keeps both legs' scores instead of collapsing them; and the full
rank_candidates pipeline sorts highest-first, skips any candidate id that
didn't survive hydration, and — deterministically, including tie-breaking —
never depends on dict/set iteration order.

Also covers the "discovery platform, not an eligibility engine" constraint
at the unit level: every scoring function here is handed profiles/
opportunities missing target_role, current_skills, career_interests, or
tags entirely, and is asserted to degrade to a 0 component rather than
raise or exclude the candidate — there is no eligibility/hard-filter logic
anywhere in this module to test for, which is itself the point.
"""

from datetime import datetime, timedelta, timezone

from app.services import ranking


def test_ranking_weights_match_product_spec_exactly():
    assert ranking.RANKING_WEIGHTS == {
        "semantic": 0.45,
        "keyword": 0.25,
        "skill_overlap": 0.10,
        "career_interest_overlap": 0.10,
        "target_role_relevance": 0.05,
        "freshness": 0.05,
    }
    assert abs(sum(ranking.RANKING_WEIGHTS.values()) - 1.0) < 1e-9


def test_build_keyword_query_is_or_joined_and_deduplicated():
    profile = {
        "target_role": "Software Engineer",
        "current_skills": ["Python", "python", "SQL"],
        "career_interests": ["Machine Learning"],
        "target_company": "Acme Corp",
        "headline": "Aspiring engineer",
    }

    query = ranking.build_keyword_query(profile)

    assert " | " in query
    terms = query.split(" | ")
    # "python" only appears once despite two case variants in current_skills.
    assert terms.count("python") == 1
    # Priority order (target_role, current_skills, career_interests,
    # target_company, headline) is preserved.
    assert terms[0] == "software"
    assert "engineer" in terms
    assert "sql" in terms
    assert "machine" in terms


def test_build_keyword_query_empty_profile_returns_empty_string():
    assert ranking.build_keyword_query({}) == ""


# ---------------------------------------------------------------------------
# skill_overlap_score
# ---------------------------------------------------------------------------


def test_skill_overlap_score_is_case_and_whitespace_insensitive():
    score, matched = ranking.skill_overlap_score(
        [" Python ", "React"], ["python", "sql", "react"]
    )

    assert score == 1.0
    assert matched == ["python", "react"]


def test_skill_overlap_score_is_punctuation_and_separator_insensitive():
    # "Node.js" (profile) vs "node-js" (tag) — dot and hyphen both collapse
    # to the same normalised "node js", so they match despite neither side
    # spelling it the same way.
    score, matched = ranking.skill_overlap_score(["Node.js"], ["node-js"])
    assert score == 1.0
    assert matched == ["node js"]

    # Same idea with underscores and a fully-compact (no separator at all)
    # variant on the other side.
    score, matched = ranking.skill_overlap_score(["Machine_Learning"], ["machinelearning"])
    assert score == 1.0
    assert matched == ["machine learning"]


def test_skill_overlap_score_partial_match():
    score, matched = ranking.skill_overlap_score(["Python", "Rust", "Go"], ["python"])

    assert score == 1 / 3
    assert matched == ["python"]


def test_skill_overlap_score_empty_skills_is_zero_not_error():
    score, matched = ranking.skill_overlap_score([], ["python"])
    assert score == 0.0
    assert matched == []


def test_skill_overlap_score_missing_tags_is_zero_not_error():
    # An opportunity with no tags at all (empty list, or None coerced to []
    # by score_candidate before this is called) never raises — it simply
    # can't contribute a skill match, same as "not an eligibility filter":
    # missing metadata degrades the component score, it doesn't exclude the
    # candidate.
    score, matched = ranking.skill_overlap_score(["Python", "SQL"], [])
    assert score == 0.0
    assert matched == []


def test_skill_overlap_score_both_empty_is_zero_not_error():
    score, matched = ranking.skill_overlap_score([], [])
    assert score == 0.0
    assert matched == []


# ---------------------------------------------------------------------------
# career_interest_overlap_score
# ---------------------------------------------------------------------------


def test_career_interest_overlap_matches_tags_directly_once_normalised():
    # "Product Management" (profile, space-separated) vs "product-management"
    # (tag, hyphenated) — previously these would NOT have matched on the
    # tags side at all (only casing/whitespace were normalised, not
    # punctuation) and had to fall back to the free-text check. Now the
    # punctuation-insensitive normalisation matches them directly.
    score, matched = ranking.career_interest_overlap_score(
        career_interests=["Product Management"],
        opportunity_tags=["product-management"],
        opportunity_text="",
    )
    assert score == 1.0
    assert matched == ["product management"]


def test_career_interest_overlap_falls_back_to_free_text_when_not_tagged():
    score, matched = ranking.career_interest_overlap_score(
        career_interests=["Machine Learning", "Product Management"],
        opportunity_tags=[],
        opportunity_text="Build machine learning pipelines at scale.",
    )

    assert "machine learning" in matched
    assert "product management" not in matched
    assert score == 0.5


def test_career_interest_overlap_score_empty_interests_is_zero_not_error():
    score, matched = ranking.career_interest_overlap_score(
        career_interests=[], opportunity_tags=["python"], opportunity_text="Python role."
    )
    assert score == 0.0
    assert matched == []


def test_career_interest_overlap_score_missing_tags_and_text_is_zero_not_error():
    score, matched = ranking.career_interest_overlap_score(
        career_interests=["Backend"], opportunity_tags=[], opportunity_text=""
    )
    assert score == 0.0
    assert matched == []


# ---------------------------------------------------------------------------
# target_role_relevance_score
# ---------------------------------------------------------------------------


def test_target_role_relevance_prefers_title_over_tags_over_org_over_description():
    title_hit = ranking.target_role_relevance_score(
        "Data Scientist", "Data Scientist Intern", [], None
    )
    tag_hit = ranking.target_role_relevance_score(
        "Data Scientist", "Summer Intern", ["data", "scientist"], None
    )
    organization_hit = ranking.target_role_relevance_score(
        "Data Scientist", "Summer Intern", [], None, "Data Scientist Collective"
    )
    description_hit = ranking.target_role_relevance_score(
        "Data Scientist", "Summer Intern", [], "Great fit for a future data scientist.", None
    )
    no_hit = ranking.target_role_relevance_score("Data Scientist", "Marketing Intern", [], None)

    assert title_hit == 1.0
    assert tag_hit == 0.7
    assert organization_hit == 0.5
    assert description_hit == 0.4
    assert no_hit == 0.0
    assert title_hit > tag_hit > organization_hit > description_hit > no_hit


def test_target_role_relevance_organization_is_additive_not_a_replacement():
    # Organization matching is on top of the other three fields, not instead
    # of them — a title match still wins even when the organization also
    # happens to match.
    score = ranking.target_role_relevance_score(
        "Data Scientist", "Data Scientist Intern", [], None, "Data Scientist Collective"
    )
    assert score == 1.0


def test_target_role_relevance_missing_target_role_is_zero_not_error():
    # No target_role at all (brand-new profile) — never raises, never
    # filters anything out, just contributes 0 to this one component.
    assert ranking.target_role_relevance_score(None, "Any Title", ["any"], "any text") == 0.0
    assert ranking.target_role_relevance_score("", "Any Title", ["any"], "any text") == 0.0


def test_target_role_relevance_missing_opportunity_fields_is_zero_not_error():
    # Every opportunity-side field missing/empty at once — still no
    # exception, just no signal.
    assert ranking.target_role_relevance_score("Data Scientist", None, [], None, None) == 0.0


def test_target_role_relevance_never_filters_just_scores_zero():
    # No overlap at all -> 0.0, not an exception/exclusion. The caller
    # (score_candidate) still blends this 0 into the total rather than
    # dropping the candidate.
    assert ranking.target_role_relevance_score(None, "Anything", [], None) == 0.0


# ---------------------------------------------------------------------------
# freshness_score
# ---------------------------------------------------------------------------


def test_freshness_score_decays_gradually_and_floors_at_zero():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    assert ranking.freshness_score(now.isoformat(), now=now) == 1.0

    quarter_window = now - timedelta(days=ranking.FRESHNESS_WINDOW_DAYS / 4)
    half_window = now - timedelta(days=ranking.FRESHNESS_WINDOW_DAYS / 2)
    three_quarter_window = now - timedelta(days=ranking.FRESHNESS_WINDOW_DAYS * 3 / 4)

    q1 = ranking.freshness_score(quarter_window.isoformat(), now=now)
    q2 = ranking.freshness_score(half_window.isoformat(), now=now)
    q3 = ranking.freshness_score(three_quarter_window.isoformat(), now=now)

    # Monotonic, gradual decline — never an abrupt cliff to 0 partway
    # through the window.
    assert 1.0 > q1 > q2 > q3 > 0.0
    assert abs(q2 - 0.5) < 1e-9

    long_ago = now - timedelta(days=ranking.FRESHNESS_WINDOW_DAYS * 3)
    assert ranking.freshness_score(long_ago.isoformat(), now=now) == 0.0


def test_freshness_score_handles_missing_and_malformed_input():
    assert ranking.freshness_score(None) == 0.0
    assert ranking.freshness_score("not-a-date") == 0.0


# ---------------------------------------------------------------------------
# normalise_leg_scores / merge_candidate_ids
# ---------------------------------------------------------------------------


def test_normalise_leg_scores_min_max_scales_into_unit_interval():
    normalised = ranking.normalise_leg_scores({"a": 1.0, "b": 3.0, "c": 5.0})

    assert normalised["a"] == 0.0
    assert normalised["b"] == 0.5
    assert normalised["c"] == 1.0


def test_normalise_leg_scores_identical_values_treated_as_all_relevant():
    normalised = ranking.normalise_leg_scores({"a": 2.0, "b": 2.0})
    assert normalised == {"a": 1.0, "b": 1.0}


def test_normalise_leg_scores_empty_input():
    assert ranking.normalise_leg_scores({}) == {}


def test_merge_candidate_ids_keeps_both_legs_scores_independently():
    semantic = [
        {"opportunity_id": "o1", "similarity": 0.9},
        {"opportunity_id": "o2", "similarity": 0.4},
    ]
    keyword = [
        {"opportunity_id": "o2", "rank": 0.2},
        {"opportunity_id": "o3", "rank": 0.1},
    ]

    semantic_by_id, keyword_by_id = ranking.merge_candidate_ids(semantic, keyword)

    assert semantic_by_id == {"o1": 0.9, "o2": 0.4}
    assert keyword_by_id == {"o2": 0.2, "o3": 0.1}


# ---------------------------------------------------------------------------
# score_candidate
# ---------------------------------------------------------------------------


def test_score_candidate_blends_all_six_components_within_unit_interval():
    opportunity = {
        "title": "Software Engineering Intern",
        "organization": "Acme Corp",
        "tags": ["python", "backend"],
        "description": "Work on backend systems in Python.",
        "posted_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    profile = {
        "current_skills": ["Python"],
        "career_interests": ["Backend"],
        "target_role": "Software Engineer",
    }

    score, reasons = ranking.score_candidate(
        opportunity=opportunity,
        profile=profile,
        semantic_similarity=0.8,
        keyword_relevance=0.6,
    )

    assert 0.0 <= score <= 1.0
    factors = {reason.factor for reason in reasons}
    assert "semantic" in factors
    assert "keyword" in factors
    assert "skill_overlap" in factors


def test_score_candidate_clamps_out_of_range_leg_scores():
    opportunity = {"title": "x", "tags": [], "description": None, "posted_at": None}
    profile = {}

    score, _ = ranking.score_candidate(
        opportunity=opportunity,
        profile=profile,
        semantic_similarity=5.0,
        keyword_relevance=-3.0,
    )

    assert 0.0 <= score <= 1.0


def test_score_candidate_empty_profile_and_opportunity_never_raises():
    # A brand-new profile (no skills, no interests, no target role) against
    # a minimally-described opportunity (no tags, no description, no
    # organization, no posted_at) — every non-retrieval component should
    # degrade to 0 rather than raising or being treated as ineligible.
    opportunity = {"title": None, "tags": None, "description": None, "posted_at": None}
    profile = {"current_skills": None, "career_interests": None, "target_role": None}

    score, reasons = ranking.score_candidate(
        opportunity=opportunity,
        profile=profile,
        semantic_similarity=0.0,
        keyword_relevance=0.0,
    )

    assert score == 0.0
    assert reasons == []


def test_score_candidate_is_deterministic_for_identical_inputs():
    # `now` must be pinned explicitly for this to be a fair "identical
    # inputs" comparison — score_candidate (via freshness_score) reads the
    # wall clock by default when `now` is omitted, so two calls a few
    # microseconds apart without it are NOT actually identical inputs. With
    # `now` fixed, everything else is a pure function of its arguments.
    now = datetime.now(tz=timezone.utc)
    opportunity = {
        "title": "Backend Engineering Intern",
        "organization": "Acme Corp",
        "tags": ["python", "backend"],
        "description": "Work on backend systems.",
        "posted_at": now.isoformat(),
    }
    profile = {
        "current_skills": ["Python"],
        "career_interests": ["Backend"],
        "target_role": "Backend Engineer",
    }
    kwargs = {
        "opportunity": opportunity,
        "profile": profile,
        "semantic_similarity": 0.73,
        "keyword_relevance": 0.42,
        "now": now,
    }

    first_score, first_reasons = ranking.score_candidate(**kwargs)
    second_score, second_reasons = ranking.score_candidate(**kwargs)

    assert first_score == second_score
    assert [r.factor for r in first_reasons] == [r.factor for r in second_reasons]


# ---------------------------------------------------------------------------
# rank_candidates
# ---------------------------------------------------------------------------


def test_rank_candidates_sorts_highest_first_and_skips_unhydrated_ids():
    now = datetime.now(tz=timezone.utc)
    opportunities = {
        "o1": {
            "title": "Great Python Match",
            "tags": ["python"],
            "description": "",
            "posted_at": now.isoformat(),
        },
        "o2": {
            "title": "Unrelated",
            "tags": [],
            "description": "",
            "posted_at": now.isoformat(),
        },
        # "o3" intentionally NOT in `opportunities` — simulates a candidate
        # that was deactivated between retrieval and hydration.
    }
    profile = {"current_skills": ["python"], "career_interests": [], "target_role": None}

    ranked = ranking.rank_candidates(
        opportunities=opportunities,
        profile=profile,
        semantic_by_id={"o1": 0.9, "o2": 0.1, "o3": 0.5},
        keyword_by_id={"o1": 0.8, "o3": 0.9},
        now=now,
    )

    ranked_ids = [row[0] for row in ranked]
    assert "o3" not in ranked_ids
    assert ranked_ids[0] == "o1"
    assert ranked[0][1] >= ranked[1][1]


def test_rank_candidates_empty_input_returns_empty_list():
    ranked = ranking.rank_candidates(
        opportunities={}, profile={}, semantic_by_id={}, keyword_by_id={}
    )
    assert ranked == []


def test_rank_candidates_breaks_ties_deterministically_by_opportunity_id():
    # Two candidates with genuinely identical scores (same semantic score,
    # no keyword/skill/interest/role/freshness signal on either side) —
    # rank_candidates must not rely on set/dict iteration order to decide
    # who comes first. Keys are inserted in descending id order on purpose,
    # so an implementation that (incorrectly) preserved insertion/hash order
    # instead of explicitly tie-breaking would return ["o2", "o1"].
    opportunities = {
        "o2": {"title": "x", "tags": [], "description": None, "posted_at": None},
        "o1": {"title": "x", "tags": [], "description": None, "posted_at": None},
    }
    profile = {}

    ranked_once = ranking.rank_candidates(
        opportunities=opportunities,
        profile=profile,
        semantic_by_id={"o2": 0.5, "o1": 0.5},
        keyword_by_id={},
    )
    ranked_twice = ranking.rank_candidates(
        opportunities=opportunities,
        profile=profile,
        semantic_by_id={"o2": 0.5, "o1": 0.5},
        keyword_by_id={},
    )

    assert [row[0] for row in ranked_once] == ["o1", "o2"]
    # Re-running with the same inputs must reproduce the same order.
    assert [row[0] for row in ranked_twice] == ["o1", "o2"]
    assert ranked_once[0][1] == ranked_once[1][1]


def test_rank_candidates_never_raises_on_missing_profile_or_opportunity_fields():
    # Every optional field absent on both sides — the whole pipeline must
    # still run to completion and return a valid ranking, not raise.
    opportunities = {
        "o1": {"title": None, "tags": None, "description": None, "posted_at": None},
    }
    profile = {"current_skills": None, "career_interests": None, "target_role": None}

    ranked = ranking.rank_candidates(
        opportunities=opportunities,
        profile=profile,
        semantic_by_id={"o1": 0.2},
        keyword_by_id={},
    )

    assert len(ranked) == 1
    assert ranked[0][0] == "o1"
    assert 0.0 <= ranked[0][1] <= 1.0
