"""Identity payloads derived from the Supabase JWT."""

from pydantic import BaseModel


class UserIdentity(BaseModel):
    id: str
    email: str | None = None
    role: str = "authenticated"
    provider: str | None = None
