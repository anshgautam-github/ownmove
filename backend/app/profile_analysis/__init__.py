"""Profile Analysis — AI career-intelligence dashboard.

A self-contained vertical slice, deliberately structured differently from
the rest of the backend (which is organised by *layer*: api/, services/,
schemas/, models/ at the top level). This module owns its own routers/,
services/, schemas/, models/ and utils/ because the feature is complex enough
(seven independent analysis sections, two swappable AI generators, its own
scoring logic) that keeping it together is easier to reason about than
spreading eight-plus files across the top-level layer folders.

Nothing outside this package should import from its internals except
`app.profile_analysis.routers.analysis_router`, which is mounted once in
`app/api/v1/router.py`. Everything else here is private to the feature.

See README.md in this directory for the full file-by-file breakdown.
"""
