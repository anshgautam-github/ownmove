"""Orchestration only — no FastAPI imports, mirrors every other Career AI
module's service in shape. Read this file first to understand the whole
feature.

Security note (binding, from the feature spec): `profile_id` is ALWAYS
`user_id` taken from the authenticated caller — never a value read from
the request body. Every conversation read/write verifies ownership via
`CoachRepository.require_conversation` (which 404s rather than 403s on a
conversation belonging to someone else, so a caller can never confirm an
id they don't own actually exists) — RLS enforces the same check again at
the database layer independently.
"""

import re

from pydantic import ValidationError

from app.ai_coach.schemas.coach import (
    CoachConversationDetail,
    CoachConversationResponse,
    CoachConversationSummary,
    CoachMessageResponse,
    CoachTurnResponse,
    SendMessageRequest,
    StartConversationRequest,
)
from app.ai_coach.services.generators.factory import get_coach_generator
from app.ai_coach.services.repository import CoachRepository
from app.ai_coach.utils.context import CoachContext
from app.core.exceptions import NotFoundError
from app.db.supabase import get_supabase

_STOPWORDS = {"the", "a", "an", "to", "my", "for", "of", "and", "is", "this", "what", "do", "does", "it", "on", "in"}


def _fallback_title(message: str) -> str:
    """Used only if the generator didn't supply `suggested_title` (e.g. a
    malformed/edge-case generation) — never leaves a conversation
    permanently titled `None`."""
    words = [w for w in re.findall(r"[A-Za-z0-9']+", message) if w.lower() not in _STOPWORDS]
    title = " ".join(words[:6]).title().strip()
    return (title or "Coaching Conversation")[:60]


def _to_conversation_response(row: dict) -> CoachConversationResponse:
    return CoachConversationResponse(
        id=row["id"],
        profile_id=row["profile_id"],
        title=row.get("title"),
        conversation_type=row.get("conversation_type"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _to_message_response(row: dict) -> CoachMessageResponse:
    return CoachMessageResponse(
        id=row["id"],
        role=row["role"],
        content=row["content"],
        structured_content=row.get("structured_content"),
        created_at=row["created_at"],
    )


async def _run_turn(
    *, repository: CoachRepository, user_id: str, conversation: dict, message: str, is_new_conversation: bool
) -> CoachTurnResponse:
    """Shared by both start_conversation and send_message: persist the
    user's message, build context, generate a reply, persist it, update
    conversation metadata, and return both new messages."""
    user_row = repository.add_message(conversation["id"], role="user", content=message)

    profile = repository.get_profile(user_id)
    experiences = repository.get_experiences(user_id)
    latest_analysis = repository.get_latest_profile_analysis(user_id)
    # Only prior messages (not the one just inserted) belong in the
    # "recent conversation" window fed back to the model.
    prior_messages = repository.list_messages(conversation["id"])[:-1]

    context = CoachContext(
        profile=profile,
        experiences=experiences,
        latest_analysis=latest_analysis,
        recent_messages=[{"role": m["role"], "content": m["content"]} for m in prior_messages],
        user_question=message,
        is_new_conversation=is_new_conversation,
    )

    generator = get_coach_generator()
    result = await generator.generate(context)

    assistant_row = repository.add_message(
        conversation["id"], role="assistant", content=result.message, structured_content=result.model_dump(mode="json")
    )

    title = conversation.get("title")
    conversation_type = conversation.get("conversation_type")
    if is_new_conversation:
        title = result.suggested_title or _fallback_title(message)
        conversation_type = result.intent
        repository.update_conversation_meta(conversation["id"], user_id, title=title, conversation_type=conversation_type)
    else:
        repository.touch_conversation(conversation["id"], user_id)

    updated = repository.get_conversation(conversation["id"], user_id) or conversation
    return CoachTurnResponse(
        conversation=_to_conversation_response(updated),
        user_message=_to_message_response(user_row),
        assistant_message=_to_message_response(assistant_row),
    )


async def start_conversation(*, user_id: str, access_token: str, request: StartConversationRequest) -> CoachTurnResponse:
    """Create a brand-new coaching conversation and answer its first
    message in one call — the landing screen's starter cards and the "Ask
    AI Coach..." box both call this."""
    client = get_supabase(access_token=access_token)
    repository = CoachRepository(client)

    conversation = repository.create_conversation(user_id)
    return await _run_turn(
        repository=repository,
        user_id=user_id,
        conversation=conversation,
        message=request.message,
        is_new_conversation=True,
    )


async def send_message(
    *, user_id: str, access_token: str, conversation_id: str, request: SendMessageRequest
) -> CoachTurnResponse:
    """Continue an existing conversation. 404s if the conversation doesn't
    exist or doesn't belong to the authenticated user."""
    client = get_supabase(access_token=access_token)
    repository = CoachRepository(client)

    conversation = repository.require_conversation(conversation_id, user_id)
    return await _run_turn(
        repository=repository,
        user_id=user_id,
        conversation=conversation,
        message=request.message,
        is_new_conversation=False,
    )


async def list_conversations(*, user_id: str, access_token: str) -> list[CoachConversationSummary]:
    """Every conversation's headline (title, type, last activity), most
    recently active first. Returns `[]` (never a 404) with no history."""
    client = get_supabase(access_token=access_token)
    repository = CoachRepository(client)

    rows = repository.list_conversations(user_id)
    return [CoachConversationSummary(**row) for row in rows]


async def get_conversation(*, user_id: str, access_token: str, conversation_id: str) -> CoachConversationDetail:
    client = get_supabase(access_token=access_token)
    repository = CoachRepository(client)

    conversation = repository.require_conversation(conversation_id, user_id)
    message_rows = repository.list_messages(conversation_id)
    try:
        messages = [_to_message_response(row) for row in message_rows]
    except ValidationError as exc:
        raise NotFoundError("This conversation could not be loaded.") from exc

    return CoachConversationDetail(**_to_conversation_response(conversation).model_dump(), messages=messages)


async def delete_conversation(*, user_id: str, access_token: str, conversation_id: str) -> None:
    client = get_supabase(access_token=access_token)
    repository = CoachRepository(client)
    repository.delete_conversation(conversation_id, user_id)
