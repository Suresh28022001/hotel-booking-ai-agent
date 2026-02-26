"""
LLM Client — wraps OpenRouter using LangChain's ChatOpenAI with custom base_url.
Handles retries and error formatting.
"""
import json
from typing import AsyncIterator, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import RateLimitError, APIConnectionError, APITimeoutError
from app.core.config import settings
from app.core.logging import logger


def get_llm(streaming: bool = False) -> ChatOpenAI:
    """Return a ChatOpenAI instance pointed at OpenRouter."""
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        streaming=streaming,
        temperature=0.3,
        max_retries=3,
        default_headers={
            "HTTP-Referer": "https://hotel-booking-agent.dev",
            "X-Title": "Hotel Booking AI Agent",
        },
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((RateLimitError, APIConnectionError, APITimeoutError)),
)
async def chat_completion(
    messages: list[BaseMessage],
    streaming: bool = False,
) -> str:
    """Send messages to LLM and return the assistant reply as a string."""
    llm = get_llm(streaming=False)
    try:
        response = await llm.ainvoke(messages)
        return response.content
    except Exception as e:
        logger.error("LLM call failed", error=str(e))
        raise


async def stream_completion(messages: list[BaseMessage]) -> AsyncIterator[str]:
    """Yield streamed tokens from the LLM."""
    llm = get_llm(streaming=True)
    async for chunk in llm.astream(messages):
        if chunk.content:
            yield chunk.content


def extract_json_from_response(text: str) -> Optional[dict]:
    """Parse JSON block from LLM response text."""
    try:
        # Try raw JSON first
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Look for ```json ... ``` block
    import re
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Last resort: find first { ... }
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None
