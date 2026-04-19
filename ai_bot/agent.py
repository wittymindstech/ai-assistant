from google.adk.agents.llm_agent import Agent
from google.genai import types
import os
import logging
from typing import Optional, Dict, Any, Tuple

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Set API key
api_key = os.environ.get('GOOGLE_API_KEY')
if not api_key:
    logger.warning("GOOGLE_API_KEY environment variable not set")
    # Try to load from environment or config
    api_key = ''

os.environ['GOOGLE_API_KEY'] = api_key

try:
    from tools import search_pdfs, search_images, extract_links, detect_objects_and_people
except Exception as e:
    logger.error(f"Error importing tools: {e}")
    raise

from google.adk.runners import InMemoryRunner
from google.genai import types


MODEL_TOKEN_LIMITS = {
    'gemini-2.5-flash': 128000,
}


def _extract_event_text(event) -> str:
    content = getattr(event, 'content', None)
    if not content:
        return ''
    text_parts = []
    if getattr(content, 'parts', None):
        for part in content.parts:
            if getattr(part, 'text', None):
                text_parts.append(part.text)
    elif getattr(content, 'text', None):
        text_parts.append(content.text)
    return ''.join(text_parts).strip()


def _format_usage_metadata(
    usage_metadata: Optional[types.GenerateContentResponseUsageMetadata],
) -> Dict[str, Any]:
    if not usage_metadata:
        return {}

    total = usage_metadata.total_token_count
    limit = MODEL_TOKEN_LIMITS.get('gemini-2.5-flash')
    remaining = None
    if total is not None and limit is not None:
        remaining = max(limit - total, 0)

    return {
        'prompt_tokens': usage_metadata.prompt_token_count,
        'response_tokens': usage_metadata.candidates_token_count,
        'total_tokens': total,
        'remaining_tokens': remaining,
        'model_token_limit': limit,
    }


def _extract_usage_info(events) -> Dict[str, Any]:
    """Find the first usage metadata available from the event list."""
    for event in reversed(events):
        usage_metadata = getattr(event, 'usage_metadata', None)
        if usage_metadata:
            return _format_usage_metadata(usage_metadata)
    return {}


async def _run_agent_query(
    query: str,
    user_id: str = 'web_user',
    session_id: str = 'web_session',
) -> Tuple[str, Dict[str, Any]]:
    runner = InMemoryRunner(agent=_root_agent)
    events = await runner.run_debug(query, user_id=user_id, session_id=session_id, quiet=True, verbose=False)
    assistant_texts = []
    for event in events:
        if getattr(event, 'author', None) == 'user':
            continue
        text = _extract_event_text(event)
        if text:
            assistant_texts.append(text)

    usage_info = _extract_usage_info(events)
    if usage_info:
        logger.info(
            f"Token usage - prompt: {usage_info.get('prompt_tokens')} "
            f"response: {usage_info.get('response_tokens')} "
            f"total: {usage_info.get('total_tokens')} "
            f"remaining: {usage_info.get('remaining_tokens')}"
        )

    return '\n'.join(assistant_texts).strip(), usage_info


async def query_agent(query: str, user_id: str = 'web_user', session_id: str = 'web_session') -> str:
    """Execute a text query through an ADK in-memory runner."""
    response, _ = await _run_agent_query(query, user_id=user_id, session_id=session_id)
    return response


async def query_agent_with_usage(
    query: str,
    user_id: str = 'web_user',
    session_id: str = 'web_session',
) -> Dict[str, Any]:
    response, usage = await _run_agent_query(query, user_id=user_id, session_id=session_id)
    return {'response': response, 'usage': usage}


# Create the root agent with error handling
try:
    _root_agent = Agent(
        model='gemini-2.5-flash',
        name='root_agent',
        description='A helpful assistant that searches local PDFs and images.',
        instruction="""
You are an AI assistant with access to local PDF documents and images.

For queries about documents or images:
1. Use search_pdfs to search through PDFs in data/pdfs/
2. Use search_images to search through images in data/images/ (combines OCR text search + vision analysis)
3. Use detect_objects_and_people to specifically identify and count people, objects, and elements in images
4. Use extract_links if the query involves finding URLs

For image-related questions:
- If user asks about people, objects, or "how many" - prioritize using detect_objects_and_people
- For text in images, use search_images

Always provide answers based on the local data first, then supplement with your general knowledge if needed.
If no relevant information is found in the local data, clearly state that and then answer from your training.

Handle errors gracefully - if a tool fails, acknowledge it and try alternative approaches.
        """,
        tools=[search_pdfs, search_images, detect_objects_and_people, extract_links],
    )
    logger.info("Root agent initialized successfully")
except Exception as e:
    logger.error(f"Error initializing agent: {e}", exc_info=True)
    raise
