"""Deprecated — kept only because files in this project's workspace can't be
deleted outright once written.

This module has gone through two lives, both now retired:

1. Originally a static, hand-picked list of benchmark programs (Google STEP,
   Microsoft Explore, MLH Fellowship, GSoC) that an "Opportunity Readiness"
   section was scored against.
2. Replaced with scoring against the *live* `public.opportunities` catalog
   instead, per a product decision that readiness should reflect what's
   actually available right now, not a fixed set of famous names.

Opportunity Readiness itself was then removed from the feature entirely —
the report doesn't include it, and neither generator computes it. Nothing
imports this module anymore; it is not part of the running feature.
"""
