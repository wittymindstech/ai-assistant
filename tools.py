import os
import re
from PIL import Image
import pytesseract
from pypdf import PdfReader


# 📄 PDF search tool
def search_pdfs(query: str) -> str:
    results = []

    for file in os.listdir("data/pdfs"):
        reader = PdfReader(f"data/pdfs/{file}")
        for page in reader.pages:
            text = page.extract_text()
            if query.lower() in text.lower():
                results.append(text[:500])

    return "\n".join(results) if results else "No PDF results found"


# 🖼️ OCR tool (images + handwritten)
def search_images(query: str) -> str:
    results = []

    for file in os.listdir("data/images"):
        img = Image.open(f"data/images/{file}")
        text = pytesseract.image_to_string(img)

        if query.lower() in text.lower():
            results.append(text[:500])

    return "\n".join(results) if results else "No image results"


# 🔗 Extract links
def extract_links(text: str) -> str:
    links = re.findall(r'https?://\S+', text)
    return "\n".join(links) if links else "No links found"
