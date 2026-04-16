from google.adk import Agent

from tools import search_pdfs, search_images, extract_links

agent = Agent(
    name="product_assistant",
    model="gemini-flash-latest",
    instruction="""
    You are an AI product assistant.

    When user asks about products:
    1. Search PDFs
    2. Search images (OCR)
    3. Extract links
    4. Return:
       - product info
       - prices
       - shopify links
    """,
    tools=[search_pdfs, search_images, extract_links],
)
