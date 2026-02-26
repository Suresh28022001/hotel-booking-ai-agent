"""
Short-term conversation memory using LangChain's in-memory store,
backed by database persistence for cross-request continuity.
"""
from typing import Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Conversation, ConversationMessage, ConversationRole
from app.core.logging import logger

# In-process cache: session_id → list[BaseMessage]
_memory_cache: dict[str, list[BaseMessage]] = {}

SYSTEM_PROMPT = """You are an expert hotel booking assistant. Your job is to help users find and book hotels.

You MUST respond with a JSON object in this exact format:
{
  "action": "search" | "book" | "cancel" | "status" | "clarify" | "greet" | "confirm",
  "reply": "Your friendly response to the user",
  "city": "city name or null",
  "check_in": "YYYY-MM-DD or null",
  "check_out": "YYYY-MM-DD or null",
  "guests": number or null,
  "budget_min": number or null,
  "budget_max": number or null,
  "star_rating": number or null,
  "amenities": ["wifi", "pool", ...] or null,
  "special_requests": "string or null",
  "confirm_hotel_id": number or null
}

Guidelines:
- If the user's request is missing required info (city, dates), set action="clarify" and ask for it in `reply`.
- If you have enough info to search, set action="search".
- If the user says "book hotel X" or confirms a hotel, set action="book" and confirm_hotel_id=<id>.
- Always be friendly, professional, and helpful.
- Extract dates in YYYY-MM-DD format.
- If user mentions budget like "$100-$200", set budget_min=100, budget_max=200.
"""


def _role_to_langchain(role: ConversationRole) -> type:
    mapping = {
        ConversationRole.USER: HumanMessage,
        ConversationRole.ASSISTANT: AIMessage,
        ConversationRole.SYSTEM: SystemMessage,
    }
    return mapping[role]


async def load_memory(session_id: str, db: AsyncSession) -> list[BaseMessage]:
    """Load conversation history from DB (or in-memory cache)."""
    if session_id in _memory_cache:
        return _memory_cache[session_id]

    result = await db.execute(
        select(Conversation).where(Conversation.session_id == session_id)
    )
    conv = result.scalar_one_or_none()

    messages: list[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT)]

    if conv:
        for msg in conv.messages:
            cls = _role_to_langchain(msg.role)
            messages.append(cls(content=msg.content))

    _memory_cache[session_id] = messages
    return messages


async def save_message(
    session_id: str,
    user_id: int,
    role: ConversationRole,
    content: str,
    db: AsyncSession,
    metadata: Optional[dict] = None,
):
    """Persist a message to DB and update in-memory cache."""
    # Get or create conversation
    result = await db.execute(
        select(Conversation).where(
            Conversation.session_id == session_id,
            Conversation.user_id == user_id,
        )
    )
    conv = result.scalar_one_or_none()

    if not conv:
        conv = Conversation(user_id=user_id, session_id=session_id)
        db.add(conv)
        await db.flush()

    msg = ConversationMessage(
        conversation_id=conv.id,
        role=role,
        content=content,
        metadata=metadata,
    )
    db.add(msg)

    # Update cache
    cls = _role_to_langchain(role)
    if session_id not in _memory_cache:
        _memory_cache[session_id] = [SystemMessage(content=SYSTEM_PROMPT)]
    _memory_cache[session_id].append(cls(content=content))


def clear_memory(session_id: str):
    _memory_cache.pop(session_id, None)
