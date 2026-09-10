"""HTTP layer for AI Coach. Thin on purpose, mirrors every other Career AI
module's router — every handler is a one-line call into coach_service,
with no business logic here.
"""

from fastapi import APIRouter, status

from app.ai_coach.schemas.coach import (
    CoachConversationDetail,
    CoachConversationSummary,
    CoachTurnResponse,
    SendMessageRequest,
    StartConversationRequest,
)
from app.ai_coach.services import coach_service
from app.api.deps import AccessToken, CurrentUser, rate_limit
from app.core.rate_limit_policy import RateLimitCategory

router = APIRouter(prefix="/career-ai/ai-coach", tags=["career-ai"])


@router.post(
    "/conversations",
    response_model=CoachTurnResponse,
    dependencies=[rate_limit(RateLimitCategory.AI_EXPENSIVE)],
)
async def create_conversation(
    request: StartConversationRequest,
    user: CurrentUser,
    access_token: AccessToken,
) -> CoachTurnResponse:
    """Start a brand-new coaching conversation and answer its first
    message. Uses OpenAI (via LangChain) if OPENAI_API_KEY is configured,
    otherwise a deterministic mock generator — see
    services/generators/factory.py.
    """
    return await coach_service.start_conversation(user_id=user.id, access_token=access_token, request=request)


@router.get(
    "/conversations",
    response_model=list[CoachConversationSummary],
    dependencies=[rate_limit(RateLimitCategory.AUTH_READ)],
)
async def read_conversations(
    user: CurrentUser,
    access_token: AccessToken,
) -> list[CoachConversationSummary]:
    """Every conversation's headline, most recently active first. Returns
    `[]` (never a 404) when there's no history yet."""
    return await coach_service.list_conversations(user_id=user.id, access_token=access_token)


@router.get(
    "/conversations/{conversation_id}",
    response_model=CoachConversationDetail,
    dependencies=[rate_limit(RateLimitCategory.AUTH_READ)],
)
async def read_conversation(
    conversation_id: str,
    user: CurrentUser,
    access_token: AccessToken,
) -> CoachConversationDetail:
    """Fetch one conversation with its full message history. 404s if it
    doesn't exist or doesn't belong to the authenticated user."""
    return await coach_service.get_conversation(user_id=user.id, access_token=access_token, conversation_id=conversation_id)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=CoachTurnResponse,
    dependencies=[rate_limit(RateLimitCategory.AI_EXPENSIVE)],
)
async def create_message(
    conversation_id: str,
    request: SendMessageRequest,
    user: CurrentUser,
    access_token: AccessToken,
) -> CoachTurnResponse:
    """Continue an existing conversation with a new user message."""
    return await coach_service.send_message(
        user_id=user.id, access_token=access_token, conversation_id=conversation_id, request=request
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[rate_limit(RateLimitCategory.AUTH_WRITE)],
)
async def remove_conversation(
    conversation_id: str,
    user: CurrentUser,
    access_token: AccessToken,
) -> None:
    """Delete a conversation (and its messages, via ON DELETE CASCADE).
    404s if it doesn't exist or doesn't belong to the authenticated user.
    """
    await coach_service.delete_conversation(user_id=user.id, access_token=access_token, conversation_id=conversation_id)
