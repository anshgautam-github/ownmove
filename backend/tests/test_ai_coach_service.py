"""Full-behavior tests for `app.ai_coach.services.coach_service` -- the
orchestration layer behind `POST /career-ai/coach/conversations`,
`POST /career-ai/coach/conversations/{id}/messages`, and the other
conversation routes.

Same convention as the other three Career AI service test files:
`get_supabase` and the module's imported `CoachRepository` are
monkeypatched to a fake bound to a shared "store" dict. The real
`MockCoachGenerator` runs unmocked.

This module has the strongest explicit IDOR pattern of the four:
`CoachRepository.require_conversation()` deliberately raises NotFoundError
(never ForbiddenError) for a conversation belonging to someone else -- "never
confirm to a caller that an id they don't own actually exists" (see
repository.py's own docstring). The tests below exercise that directly
through `send_message`/`get_conversation`/`delete_conversation`, not just
by asserting on the repository in isolation.
"""

import itertools

import pytest

from app.ai_coach.schemas.coach import SendMessageRequest, StartConversationRequest
from app.ai_coach.services import coach_service as service_module
from app.ai_coach.services.generators.mock_generator import MockCoachGenerator
from app.core.exceptions import NotFoundError

_MODULE = "app.ai_coach.services.coach_service"


def _profile(**overrides) -> dict:
    profile = {
        "id": "user-1",
        "full_name": "Riya Sharma",
        "headline": "CS student",
        "bio": "Building things and learning as I go.",
        "education_level": "Undergraduate",
        "degree": "B.Tech",
        "major": "Computer Science",
        "branch": None,
        "college_name": "Example Institute of Technology",
        "graduation_year": 2027,
        "graduation_status": "in_progress",
        "target_role": "Backend Engineer",
        "target_company": None,
        "career_interests": ["Backend"],
        "current_skills": ["Python", "SQL"],
        "github_url": None,
        "resume_url": None,
        "linkedin_url": None,
        "ai_profile_summary": None,
    }
    profile.update(overrides)
    return profile


def _make_fake_repository_class(store: dict):
    ids = itertools.count(1)
    msg_ids = itertools.count(1)

    class FakeCoachRepository:
        def __init__(self, client):
            self._client = client

        def get_profile(self, profile_id: str) -> dict:
            profile = store["profiles"].get(profile_id)
            if profile is None:
                raise NotFoundError("Complete your profile before using AI Coach.")
            return profile

        def get_experiences(self, profile_id: str) -> list[dict]:
            return list(store["experiences"].get(profile_id, []))

        def get_latest_profile_analysis(self, profile_id: str) -> dict | None:
            return store["latest_analysis"].get(profile_id)

        def create_conversation(self, profile_id: str) -> dict:
            conv_id = f"conv-{next(ids)}"
            row = {
                "id": conv_id,
                "profile_id": profile_id,
                "title": None,
                "conversation_type": None,
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
            }
            store["conversations"][conv_id] = row
            store["messages"][conv_id] = []
            return row

        def get_conversation(self, conversation_id: str, profile_id: str) -> dict | None:
            row = store["conversations"].get(conversation_id)
            if row is None or row["profile_id"] != profile_id:
                return None
            return row

        def require_conversation(self, conversation_id: str, profile_id: str) -> dict:
            conversation = self.get_conversation(conversation_id, profile_id)
            if conversation is None:
                raise NotFoundError("That conversation could not be found.")
            return conversation

        def list_conversations(self, profile_id: str, limit: int = 30) -> list[dict]:
            rows = [c for c in store["conversations"].values() if c["profile_id"] == profile_id]
            rows.sort(key=lambda c: c["updated_at"], reverse=True)
            return [
                {
                    "id": c["id"],
                    "title": c["title"],
                    "conversation_type": c["conversation_type"],
                    "updated_at": c["updated_at"],
                }
                for c in rows[:limit]
            ]

        def _bump_updated_at(self, conversation_id: str) -> str:
            n_messages = len(store["messages"].get(conversation_id, []))
            return f"2026-01-01T00:0{n_messages}:00+00:00"

        def update_conversation_meta(
            self, conversation_id, profile_id, *, title, conversation_type
        ) -> None:
            row = store["conversations"].get(conversation_id)
            if row is None or row["profile_id"] != profile_id:
                return
            if title is not None:
                row["title"] = title
            if conversation_type is not None:
                row["conversation_type"] = conversation_type
            row["updated_at"] = self._bump_updated_at(conversation_id)

        def touch_conversation(self, conversation_id: str, profile_id: str) -> None:
            row = store["conversations"].get(conversation_id)
            if row is not None and row["profile_id"] == profile_id:
                row["updated_at"] = self._bump_updated_at(conversation_id)

        def delete_conversation(self, conversation_id: str, profile_id: str) -> None:
            row = store["conversations"].get(conversation_id)
            if row is None or row["profile_id"] != profile_id:
                raise NotFoundError("That conversation could not be found.")
            del store["conversations"][conversation_id]
            store["messages"].pop(conversation_id, None)

        def list_messages(self, conversation_id: str) -> list[dict]:
            return list(store["messages"].get(conversation_id, []))

        def add_message(self, conversation_id, *, role, content, structured_content=None) -> dict:
            row = {
                "id": f"msg-{next(msg_ids)}",
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "structured_content": structured_content,
                "created_at": "2026-01-01T00:00:00+00:00",
            }
            store["messages"].setdefault(conversation_id, []).append(row)
            return row

    return FakeCoachRepository


def _wire(monkeypatch, store: dict):
    monkeypatch.setattr(f"{_MODULE}.get_supabase", lambda access_token=None: object())
    monkeypatch.setattr(f"{_MODULE}.CoachRepository", _make_fake_repository_class(store))
    # Force the deterministic mock generator regardless of a real
    # OPENAI_API_KEY in the developer's own .env -- see the matching comment
    # in tests/test_profile_analysis_service.py._wire for why patching the
    # factory function (not settings) is required here. Without this, these
    # tests silently made real network calls to OpenAI on a machine with a
    # real key configured -- they still happened to pass (nothing here
    # asserted on which generator ran), which is exactly why this needed a
    # deliberate fix rather than being caught by a red test.
    monkeypatch.setattr(f"{_MODULE}.get_coach_generator", lambda: MockCoachGenerator())


def _new_store() -> dict:
    return {
        "profiles": {},
        "experiences": {},
        "latest_analysis": {},
        "conversations": {},
        "messages": {},
    }


async def _start(user_id: str, message: str):
    return await service_module.start_conversation(
        user_id=user_id, access_token="token", request=StartConversationRequest(message=message)
    )


# ---------------------------------------------------------------------------
# start_conversation
# ---------------------------------------------------------------------------


async def test_start_conversation_happy_path_sets_title_and_type(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile()

    response = await service_module.start_conversation(
        user_id="user-1",
        access_token="token",
        request=StartConversationRequest(message="Should I learn Kubernetes or Go next?"),
    )

    assert response.user_message.role == "user"
    assert response.assistant_message.role == "assistant"
    assert response.conversation.title  # set on first turn
    assert response.conversation.conversation_type is not None


async def test_start_conversation_raises_not_found_for_a_missing_profile(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)

    with pytest.raises(NotFoundError):
        await service_module.start_conversation(
            user_id="user-1",
            access_token="token",
            request=StartConversationRequest(message="What should I focus on?"),
        )


async def test_start_conversation_persists_both_messages(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile()

    response = await service_module.start_conversation(
        user_id="user-1",
        access_token="token",
        request=StartConversationRequest(message="Is a hackathon worth my time this month?"),
    )

    messages = store["messages"][response.conversation.id]
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[0]["content"] == "Is a hackathon worth my time this month?"


# ---------------------------------------------------------------------------
# send_message -- continuing a conversation, and IDOR
# ---------------------------------------------------------------------------


async def test_send_message_continues_an_existing_conversation(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile()
    first = await _start("user-1", "What should I build next?")

    second = await service_module.send_message(
        user_id="user-1",
        access_token="token",
        conversation_id=first.conversation.id,
        request=SendMessageRequest(message="What if I only have 5 hours a week?"),
    )

    assert second.conversation.id == first.conversation.id
    assert len(store["messages"][first.conversation.id]) == 4  # 2 turns x (user + assistant)


async def test_send_message_does_not_reset_title_on_later_turns(monkeypatch):
    # suggested_title/intent are only ever set on the FIRST turn -- a later
    # turn must call touch_conversation (bump updated_at only), never
    # update_conversation_meta again, so an established title is never
    # silently overwritten mid-conversation.
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile()
    first = await _start("user-1", "What should I build next?")
    original_title = first.conversation.title
    assert original_title

    second = await service_module.send_message(
        user_id="user-1",
        access_token="token",
        conversation_id=first.conversation.id,
        request=SendMessageRequest(message="What if I only have 5 hours a week?"),
    )

    assert second.conversation.title == original_title


async def test_send_message_raises_not_found_for_a_nonexistent_conversation(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile()

    with pytest.raises(NotFoundError):
        await service_module.send_message(
            user_id="user-1",
            access_token="token",
            conversation_id="does-not-exist",
            request=SendMessageRequest(message="Hello?"),
        )


async def test_send_message_raises_not_found_not_forbidden_for_anothers_conversation(monkeypatch):
    # The core IDOR guarantee of this module: require_conversation() must
    # 404, never 403, for a conversation genuinely owned by someone else --
    # so an attacker learns nothing about whether the id even exists.
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile(id="user-1")
    store["profiles"]["user-2"] = _profile(id="user-2")
    victim = await _start("user-1", "My private question")

    with pytest.raises(NotFoundError):
        await service_module.send_message(
            user_id="user-2",
            access_token="token",
            conversation_id=victim.conversation.id,
            request=SendMessageRequest(
                message="attacker trying to read/continue someone else's conversation"
            ),
        )
    # And nothing was appended to the victim's conversation as a side effect
    # of the attempt.
    assert len(store["messages"][victim.conversation.id]) == 2


# ---------------------------------------------------------------------------
# list_conversations
# ---------------------------------------------------------------------------


async def test_list_conversations_returns_empty_list_not_an_error(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile()

    conversations = await service_module.list_conversations(user_id="user-1", access_token="token")

    assert conversations == []


async def test_list_conversations_only_returns_the_callers_own(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile(id="user-1")
    store["profiles"]["user-2"] = _profile(id="user-2")
    await _start("user-1", "Question from user 1")
    await _start("user-2", "Question from user 2")

    conversations = await service_module.list_conversations(user_id="user-1", access_token="token")

    assert len(conversations) == 1


# ---------------------------------------------------------------------------
# get_conversation -- IDOR
# ---------------------------------------------------------------------------


async def test_get_conversation_returns_the_owners_own_with_messages(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile()
    created = await _start("user-1", "What should I do?")

    detail = await service_module.get_conversation(
        user_id="user-1", access_token="token", conversation_id=created.conversation.id
    )

    assert detail.id == created.conversation.id
    assert len(detail.messages) == 2


async def test_get_conversation_raises_not_found_not_forbidden_for_anothers(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile(id="user-1")
    store["profiles"]["user-2"] = _profile(id="user-2")
    victim = await _start("user-1", "My private question")

    with pytest.raises(NotFoundError):
        await service_module.get_conversation(
            user_id="user-2", access_token="token", conversation_id=victim.conversation.id
        )


# ---------------------------------------------------------------------------
# delete_conversation -- IDOR
# ---------------------------------------------------------------------------


async def test_delete_conversation_removes_the_owners_own(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile()
    created = await _start("user-1", "What should I do?")

    await service_module.delete_conversation(
        user_id="user-1", access_token="token", conversation_id=created.conversation.id
    )

    assert created.conversation.id not in store["conversations"]


async def test_delete_conversation_raises_not_found_and_does_not_delete_anothers(monkeypatch):
    store = _new_store()
    _wire(monkeypatch, store)
    store["profiles"]["user-1"] = _profile(id="user-1")
    store["profiles"]["user-2"] = _profile(id="user-2")
    victim = await _start("user-1", "My private question")

    with pytest.raises(NotFoundError):
        await service_module.delete_conversation(
            user_id="user-2", access_token="token", conversation_id=victim.conversation.id
        )

    assert victim.conversation.id in store["conversations"]  # untouched
