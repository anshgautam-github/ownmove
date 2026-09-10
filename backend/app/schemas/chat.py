"""AI chat assistant contracts."""

from typing import Literal

from pydantic import BaseModel, Field

Role = Literal["user", "assistant", "system"]


class ChatMessage(BaseModel):
    role: Role
    content: str


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str
    # When true the assistant grounds answers in the user's profile and the
    # opportunity corpus via the RAG pipeline.
    use_rag: bool = True


class Citation(BaseModel):
    source_id: str
    source_type: str
    snippet: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    message: ChatMessage
    citations: list[Citation] = Field(default_factory=list)
