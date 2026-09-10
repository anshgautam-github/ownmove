/**
 * Deprecated — "Evidence Credibility" was replaced by "Recruiter Signals"
 * (see RecruiterSignalsCard.jsx). That section's verified/partially_verified
 * language implied this platform checked the actual contents of a GitHub
 * repo, a resume file, or a LinkedIn profile — it never did. Recruiter
 * Signals makes no verification claim at all: it names a fixed, 10-item
 * vocabulary of things a recruiter is likely to notice scanning the profile,
 * each with a named status tier (Strong/Moderate/Limited/Missing/Unknown)
 * instead of an invented confidence percentage.
 *
 * Kept in place (empty of logic) rather than deleted since files already
 * written to this workspace can't be removed outright. Nothing imports
 * this file — see ProfileAnalysisDashboard.jsx, which renders
 * RecruiterSignalsCard instead.
 */
export {};
