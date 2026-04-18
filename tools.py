import os
import re
import logging
import json
import zipfile
from PIL import Image
import pytesseract
from pypdf import PdfReader

logger = logging.getLogger(__name__)


def _extract_text_from_pages(file_path: str) -> str:
    """Extract text content from Apple Pages (.pages) files."""
    try:
        with zipfile.ZipFile(file_path, 'r') as pages_zip:
            # Try to read the index.json or document.json files
            try:
                if 'index.json' in pages_zip.namelist():
                    with pages_zip.open('index.json') as f:
                        data = json.load(f)
                        if isinstance(data, dict) and 'documentMetadata' in data:
                            return json.dumps(data, indent=2)[:2000]
            except:
                pass
            
            # Extract plain text if available
            text_content = []
            for name in pages_zip.namelist():
                if name.endswith('.txt'):
                    try:
                        with pages_zip.open(name) as f:
                            text_content.append(f.read().decode('utf-8', errors='ignore'))
                    except:
                        continue
            
            if text_content:
                return '\n'.join(text_content)[:2000]
            
            # If no plain text, return file info
            return f"Pages file detected. Files in archive: {', '.join(pages_zip.namelist()[:5])}"
    except Exception as e:
        logger.error(f"Error extracting from Pages file: {str(e)}")
        return f"Error reading Pages file: {str(e)}"


def _get_available_documents() -> str:
    """Get a list of available documents in data/pdfs directory."""
    try:
        pdf_dir = "data/pdfs"
        if not os.path.exists(pdf_dir):
            return "PDF directory not found"
        
        files = os.listdir(pdf_dir)
        if not files:
            return "No documents available in data/pdfs/"
        
        file_info = []
        for f in sorted(files):
            if os.path.isfile(os.path.join(pdf_dir, f)):
                ext = os.path.splitext(f)[1].lower()
                file_info.append(f"{f} ({ext})")
        
        return "Available documents: " + ", ".join(file_info) if file_info else "No documents found"
    except Exception as e:
        return f"Error listing documents: {str(e)}"


# 📄 PDF search tool
def search_pdfs(query: str) -> str:
    """Search through PDF documents and other supported formats for matching content."""
    results = []
    
    try:
        pdf_dir = "data/pdfs"
        if not os.path.exists(pdf_dir):
            return "PDF directory not found. " + _get_available_documents()
        
        files = os.listdir(pdf_dir)
        if not files:
            return "No documents available. " + _get_available_documents()
        
        for file in sorted(files):
            file_path = os.path.join(pdf_dir, file)
            
            if not os.path.isfile(file_path):
                continue
            
            ext = os.path.splitext(file)[1].lower()
            
            # Handle PDF files
            if ext == '.pdf':
                try:
                    reader = PdfReader(file_path)
                    for page_num, page in enumerate(reader.pages):
                        text = page.extract_text()
                        if text and query.lower() in text.lower():
                            results.append(f"[PDF: {file}, page {page_num+1}] {text[:500]}")
                except Exception as e:
                    logger.error(f"Error reading PDF {file}: {str(e)}")
                    continue
            
            # Handle Pages files (.pages)
            elif ext == '.pages':
                try:
                    content = _extract_text_from_pages(file_path)
                    if query.lower() in content.lower():
                        results.append(f"[Pages: {file}] {content[:500]}")
                except Exception as e:
                    logger.error(f"Error reading Pages file {file}: {str(e)}")
                    continue
        
        if results:
            return "\n\n".join(results)
        else:
            # No matching content found, but list what's available
            available = _get_available_documents()
            return f"No matching content found for '{query}'.\n{available}"
    except Exception as e:
        logger.error(f"Error in search_pdfs: {str(e)}")
        return f"Error searching documents: {str(e)}"


# 🖼️ OCR tool (images + handwritten)
def search_images(query: str) -> str:
    """Search through images using OCR for matching content."""
    results = []
    
    try:
        img_dir = "data/images"
        if not os.path.exists(img_dir):
            return "Images directory not found"
        
        if not os.listdir(img_dir):
            return "No images available"
        
        for file in os.listdir(img_dir):
            if not file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                continue
            
            try:
                file_path = os.path.join(img_dir, file)
                img = Image.open(file_path)
                text = pytesseract.image_to_string(img)
                
                if text and query.lower() in text.lower():
                    results.append(f"[From {file}] {text[:500]}")
            except Exception as e:
                logger.error(f"Error processing image {file}: {str(e)}")
                continue
        
        return "\n".join(results) if results else "No matching content found in images"
    except Exception as e:
        logger.error(f"Error in search_images: {str(e)}")
        return f"Error searching images: {str(e)}"


# 🔗 Extract links
def extract_links(text: str) -> str:
    """Extract URLs from the given text."""
    try:
        links = re.findall(r'https?://\S+', text)
        return "\n".join(links) if links else "No links found"
    except Exception as e:
        logger.error(f"Error in extract_links: {str(e)}")
        return f"Error extracting links: {str(e)}"
