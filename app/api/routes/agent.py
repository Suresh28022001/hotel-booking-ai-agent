from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.schemas.schemas import ChatMessage, ChatResponse
from app.agent.agent import hotel_agent
from app.core.security import get_current_user_id
from app.core.logging import logger
import json

router = APIRouter(prefix="/agent", tags=["AI Agent"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatMessage,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Main chat endpoint. Sends a message to the AI agent and returns a structured response.
    The agent extracts booking intent, calls tools, and returns hotels or booking confirmation.
    """
    logger.info("Chat request", user_id=user_id, session_id=body.session_id)
    response = await hotel_agent.run(
        user_message=body.message,
        user_id=user_id,
        session_id=body.session_id,
        db=db,
    )
    return response


@router.post("/chat/stream")
async def chat_stream(
    body: ChatMessage,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Streaming chat endpoint — yields tokens as Server-Sent Events.
    Note: Tool calls happen after streaming completes.
    """
    from app.agent.llm_client import stream_completion
    from app.agent.memory import load_memory, save_message
    from app.models.models import ConversationRole
    from langchain_core.messages import HumanMessage
    import uuid

    session_id = body.session_id or str(uuid.uuid4())
    messages = await load_memory(session_id, db)
    messages.append(HumanMessage(content=body.message))

    async def event_generator():
        full_response = ""
        yield f"data: {json.dumps({'session_id': session_id})}\n\n"
        async for token in stream_completion(messages):
            full_response += token
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

        # Persist after streaming
        await save_message(session_id, user_id, ConversationRole.USER, body.message, db)
        await save_message(session_id, user_id, ConversationRole.ASSISTANT, full_response, db)
        await db.commit()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
