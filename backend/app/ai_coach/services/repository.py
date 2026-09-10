"""Supabase I/O for coach_conversations + coach_messages — the only file in
this feature that imports the Supabase client directly.

Always constructed with a user-scoped client (`db.supabase.get_supabase(
access_token=...)`), never the service-role client: profiles, experiences,
profile_analysis, coach_conversations, and coach_messages are all rows the
requesting user owns, so this runs under the same Row Level Security every
direct-from-browser query does. See policies/007_rls_ai_coach.sql.
`profile_id` is always sourced from the authenticated user (`user.id` in
the router/service layer), never from client-supplied request data.
"""

from datetime import datetime, timezone

from supabase import Client

from app.core.exceptions import ExternalServiceError, NotFoundError


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CoachRepository:
    def __init__(self, client: Client):
        self._client = client

    # ---- shared profile context reads (same pattern as career_roadmap /
    # career_simulation's own repositories — independent copies, not a
    # shared import, per each module's own convention) ----------------------

    def get_profile(self, profile_id: str) -> dict:
        response = self._client.table("profiles").select("*").eq("id", profile_id).maybe_single().execute()
        if not response or not response.data:
            raise NotFoundError("Complete your profile before using AI Coach.")
        return response.data

    def get_experiences(self, profile_id: str) -> list[dict]:
        response = (
            self._client.table("experiences")
            .select("*")
            .eq("profile_id", profile_id)
            .order("created_at")
            .order("id")
            .execute()
        )
        return response.data or []

    def get_latest_profile_analysis(self, profile_id: str) -> dict | None:
        response = (
            self._client.table("profile_analysis")
            .select("*")
            .eq("profile_id", profile_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    # ---- conversations ------------------------------------------------------

    def create_conversation(self, profile_id: str) -> dict:
        """Created with no title/type yet — the first assistant reply fills
        both in via `update_conversation_meta` once the generator has
        classified the turn and (optionally) suggested a title."""
        response = self._client.table("coach_conversations").insert({"profile_id": profile_id}).execute()
        if not response.data:
            raise ExternalServiceError("Failed to start a new coaching conversation.")
        return response.data[0]

    def get_conversation(self, conversation_id: str, profile_id: str) -> dict | None:
        response = (
            self._client.table("coach_conversations")
            .select("*")
            .eq("id", conversation_id)
            .eq("profile_id", profile_id)
            .maybe_single()
            .execute()
        )
        return response.data if response else None

    def require_conversation(self, conversation_id: str, profile_id: str) -> dict:
        """Raises NotFoundError rather than ForbiddenError when the
        conversation belongs to someone else — never confirm to a caller
        that an id they don't own actually exists."""
        conversation = self.get_conversation(conversation_id, profile_id)
        if conversation is None:
            raise NotFoundError("That conversation could not be found.")
        return conversation

    def list_conversations(self, profile_id: str, limit: int = 30) -> list[dict]:
        response = (
            self._client.table("coach_conversations")
            .select("id,title,conversation_type,updated_at")
            .eq("profile_id", profile_id)
            .order("updated_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []

    def update_conversation_meta(self, conversation_id: str, profile_id: str, *, title: str | None, conversation_type: str | None) -> None:
        """Best-effort — only sets `title`/`conversation_type` the first
        time (when both are still null), and always bumps `updated_at` so
        the history list sorts by recent activity."""
        update: dict = {"updated_at": _now_iso()}
        if title is not None:
            update["title"] = title
        if conversation_type is not None:
            update["conversation_type"] = conversation_type
        self._client.table("coach_conversations").update(update).eq("id", conversation_id).eq(
            "profile_id", profile_id
        ).execute()

    def touch_conversation(self, conversation_id: str, profile_id: str) -> None:
        self._client.table("coach_conversations").update({"updated_at": _now_iso()}).eq("id", conversation_id).eq(
            "profile_id", profile_id
        ).execute()

    def delete_conversation(self, conversation_id: str, profile_id: str) -> None:
        response = (
            self._client.table("coach_conversations")
            .delete()
            .eq("id", conversation_id)
            .eq("profile_id", profile_id)
            .execute()
        )
        if not response.data:
            # Either it never existed or belonged to someone else — same
            # NotFoundError either way, never confirm existence to a
            # non-owner.
            raise NotFoundError("That conversation could not be found.")

    # ---- messages -------------------------------------------------------------

    def list_messages(self, conversation_id: str) -> list[dict]:
        response = (
            self._client.table("coach_messages")
            .select("*")
            .eq("conversation_id", conversation_id)
            .order("created_at")
            .order("id")
            .execute()
        )
        return response.data or []

    def add_message(self, conversation_id: str, *, role: str, content: str, structured_content: dict | None = None) -> dict:
        row = {"conversation_id": conversation_id, "role": role, "content": content}
        if structured_content is not None:
            row["structured_content"] = structured_content
        response = self._client.table("coach_messages").insert(row).execute()
        if not response.data:
            raise ExternalServiceError("Failed to save the conversation message.")
        return response.data[0]
