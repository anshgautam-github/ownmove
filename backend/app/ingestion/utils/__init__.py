"""Reusable, source-agnostic helpers shared by every agent.

Nothing here knows about any particular opportunity source — that keeps
these importable from `app/ingestion/agents/*` without ever creating a
dependency in the other direction.
"""
