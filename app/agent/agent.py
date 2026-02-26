"""
Hotel Booking Agent — ReAct-style agent using LangGraph.

Flow:
  User message → Load memory → LLM (intent extraction + JSON response)
  → Parse action → Execute tool → Format final reply → Save memory → Return

The agent uses a structured JSON response format instead of native tool calling
for compatibility with the free OpenRouter model.
"""
import uuid
from typing import Optional
from langchain_core.messages import HumanMessage, AIMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.llm_client import chat_completion, extract_json_from_response
from app.agent.memory import load_memory, save_message
from app.agent.tools import tool_search_hotels, tool_book_hotel, tool_get_bookings
from app.models.models import ConversationRole
from app.schemas.schemas import BookingIntent, ChatResponse, HotelOut, BookingOut
from app.core.logging import logger


class HotelBookingAgent:
    """
    Agent Architecture:
    ─────────────────────────────────────────────────────────────────
    1. MEMORY LOAD    → Pull conversation history for session
    2. LLM CALL       → Send history + new user message to LLM
                        LLM returns structured JSON with:
                        - action (search/book/clarify/status/greet)
                        - reply (user-facing text)
                        - extracted params (city, dates, budget, etc.)
    3. TOOL DISPATCH  → Based on `action`, call the matching tool:
                        - search  → tool_search_hotels()
                        - book    → tool_book_hotel()
                        - status  → tool_get_bookings()
                        - clarify → no tool, just return reply
    4. RESPONSE BUILD → Combine LLM reply + tool results
    5. MEMORY SAVE    → Persist user + assistant messages to DB
    ─────────────────────────────────────────────────────────────────
    """

    async def run(
        self,
        user_message: str,
        user_id: int,
        session_id: Optional[str],
        db: AsyncSession,
    ) -> ChatResponse:
        # 1. Session management
        if not session_id:
            session_id = str(uuid.uuid4())

        # 2. Load conversation memory
        messages = await load_memory(session_id, db)
        messages.append(HumanMessage(content=user_message))

        # 3. Call LLM
        logger.info("Agent LLM call", session_id=session_id, action="pending")
        raw_response = await chat_completion(messages)
        logger.info("Agent LLM response received", session_id=session_id)

        # 4. Parse structured JSON from LLM
        parsed = extract_json_from_response(raw_response)
        if not parsed:
            # Fallback if LLM didn't return valid JSON
            parsed = {"action": "clarify", "reply": raw_response}

        action = parsed.get("action", "clarify")
        reply = parsed.get("reply", "I'm here to help! What are you looking for?")

        intent = BookingIntent(
            city=parsed.get("city"),
            check_in=parsed.get("check_in"),
            check_out=parsed.get("check_out"),
            guests=parsed.get("guests"),
            budget_min=parsed.get("budget_min"),
            budget_max=parsed.get("budget_max"),
            star_rating=parsed.get("star_rating"),
            amenities=parsed.get("amenities"),
            special_requests=parsed.get("special_requests"),
            confirm_hotel_id=parsed.get("confirm_hotel_id"),
            action=action,
        )

        # 5. Tool dispatch
        suggested_hotels: Optional[list[HotelOut]] = None
        booking: Optional[BookingOut] = None
        booking_initiated = False

        if action == "search":
            suggested_hotels = await tool_search_hotels(intent, db)
            if suggested_hotels:
                hotel_list = "\n".join(
                    f"- #{h.id} {h.name} ({h.star_rating}★) — ${h.price_per_night}/night in {h.city}"
                    for h in suggested_hotels
                )
                reply += f"\n\nHere are the best matches I found:\n{hotel_list}\n\nWould you like to book any of these?"
            else:
                reply = "I couldn't find any hotels matching your criteria. Would you like to adjust your search?"

        elif action == "book":
            hotel_id = intent.confirm_hotel_id
            if hotel_id and intent.check_in and intent.check_out:
                booking = await tool_book_hotel(user_id, hotel_id, intent, db)
                if booking:
                    booking_initiated = True
                    reply = (
                        f"🎉 Your booking is confirmed!\n"
                        f"Hotel: {booking.hotel.name if booking.hotel else 'N/A'}\n"
                        f"Check-in: {booking.check_in.strftime('%b %d, %Y')}\n"
                        f"Check-out: {booking.check_out.strftime('%b %d, %Y')}\n"
                        f"Guests: {booking.guests}\n"
                        f"Total: ${booking.total_price:.2f}\n"
                        f"Booking ID: #{booking.id}"
                    )
                else:
                    reply = "Sorry, I couldn't complete the booking. The hotel may no longer be available."
            else:
                reply = "To complete your booking, I need the hotel selection and your check-in/check-out dates. Could you confirm those?"

        elif action == "status":
            bookings = await tool_get_bookings(user_id, db)
            if bookings:
                items = "\n".join(
                    f"- #{b.id} {b.hotel.name if b.hotel else 'Hotel'} "
                    f"({b.check_in.strftime('%b %d')} → {b.check_out.strftime('%b %d')}) [{b.status}]"
                    for b in bookings
                )
                reply = f"Here are your bookings:\n{items}"
            else:
                reply = "You don't have any bookings yet. Would you like me to help you find a hotel?"

        # 6. Save to memory & DB
        await save_message(session_id, user_id, ConversationRole.USER, user_message, db)
        await save_message(session_id, user_id, ConversationRole.ASSISTANT, reply, db, metadata=parsed)

        return ChatResponse(
            reply=reply,
            session_id=session_id,
            suggested_hotels=suggested_hotels,
            booking_initiated=booking_initiated,
            booking=booking,
        )


# Singleton agent instance
hotel_agent = HotelBookingAgent()
