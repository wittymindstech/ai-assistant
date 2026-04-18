from google.adk.agents.llm_agent import Agent
import os
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Set API key
api_key = os.environ.get('GOOGLE_API_KEY')
if not api_key:
    logger.warning("GOOGLE_API_KEY environment variable not set")
    # Try to load from environment or config
    api_key = 'AQ.Ab8RN6KKHQno2jBHCaRMl2vJ0LLQb916IE7GRCtdo4oNKAMtFQ'

os.environ['GOOGLE_API_KEY'] = api_key

try:
    from tools import search_pdfs, search_images, extract_links
except Exception as e:
    logger.error(f"Error importing tools: {e}")
    raise

from google.adk.runners import InMemoryRunner
from google.genai import types


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


async def query_agent(query: str, user_id: str = 'web_user', session_id: str = 'web_session') -> str:
    """Execute a text query through an ADK in-memory runner."""
    runner = InMemoryRunner(agent=_root_agent)
    events = await runner.run_debug(query, user_id=user_id, session_id=session_id, quiet=True, verbose=False)
    assistant_texts = []
    for event in events:
        if getattr(event, 'author', None) == 'user':
            continue
        text = _extract_event_text(event)
        if text:
            assistant_texts.append(text)
    return '\n'.join(assistant_texts).strip()


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
2. Use search_images to search through images in data/images/
3. Use extract_links if the query involves finding URLs

Always provide answers based on the local data first, then supplement with your general knowledge if needed.
If no relevant information is found in the local data, clearly state that and then answer from your training.

Handle errors gracefully - if a tool fails, acknowledge it and try alternative approaches.
        """,
        tools=[search_pdfs, search_images, extract_links],
    )
    logger.info("Root agent initialized successfully")
except Exception as e:
    logger.error(f"Error initializing agent: {e}", exc_info=True)
    raise
