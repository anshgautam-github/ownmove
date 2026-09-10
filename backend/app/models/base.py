"""Domain models.

These describe rows as they exist in Postgres. They are intentionally
separate from `schemas/` (the wire contract) so the database shape can change
without breaking the public API, and vice versa.

Supabase owns the actual DDL — see /supabase for the version-controlled
schema, policies and migrations.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DBModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampedModel(DBModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None
