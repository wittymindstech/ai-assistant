import os
import re
import logging
import json
import zipfile
import base64
from PIL import Image
import pytesseract
from pypdf import PdfReader
import google.genai as genai

logger = logging.getLogger(__name__)

# Initialize Gemini for vision analysis
api_key = os.environ.get('GOOGLE_API_KEY')
if api_key:
    genai.configure(api_key=api_key)


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


# 🖼️ Vision analysis - detect objects and people
def _analyze_image_with_vision(image_path: str) -> str:
    """Analyze an image using Gemini's vision capabilities to detect objects, people, and other elements."""
    try:
        # Read and prepare the image
        with open(image_path, 'rb') as img_file:
            image_data = base64.standard_b64encode(img_file.read()).decode('utf-8')
        
        # Determine MIME type from file extension
        ext = os.path.splitext(image_path)[1].lower()
        mime_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp',
        }
        mime_type = mime_type_map.get(ext, 'image/jpeg')
        
        # Use Gemini to analyze the image
        client = genai.Client()
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                {
                    'role': 'user',
                    'parts': [
                        {
                            'inline_data': {
                                'mime_type': mime_type,
                                'data': image_data
                            }
                        },
                        'Please analyze this image and provide: 1) Count and identify any people (e.g., "2 people standing"), 2) List all visible objects and items, 3) Brief description of the scene. Format the response clearly.'
                    ]
                }
            ]
        )
        
        if response.candidates:
            return response.candidates[0].content.parts[0].text
        return "No analysis available"
    except Exception as e:
        logger.error(f"Error analyzing image with vision: {str(e)}")
        return f"Vision analysis error: {str(e)}"


# 🖼️ Search images - OCR + vision analysis
def search_images(query: str) -> str:
    """Search through images using OCR and vision analysis to detect objects, people, and text."""
    results = []
    
    try:
        img_dir = "data/images"
        if not os.path.exists(img_dir):
            return "Images directory not found"
        
        images = [f for f in os.listdir(img_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
        if not images:
            return "No images available in data/images/"
        
        for file in sorted(images):
            file_path = os.path.join(img_dir, file)
            result_entry = f"\n📷 {file}:\n"
            match_found = False
            
            # 1. OCR-based text search
            try:
                img = Image.open(file_path)
                ocr_text = pytesseract.image_to_string(img)
                
                if ocr_text and query.lower() in ocr_text.lower():
                    result_entry += f"  [OCR Text Match] {ocr_text[:300]}\n"
                    match_found = True
            except Exception as e:
                logger.error(f"Error running OCR on {file}: {str(e)}")
            
            # 2. Vision-based object and people detection
            try:
                vision_analysis = _analyze_image_with_vision(file_path)
                result_entry += f"  [Vision Analysis]\n{vision_analysis}\n"
                
                # Check if query matches vision analysis (for objects, people, etc.)
                if query.lower() in vision_analysis.lower():
                    match_found = True
            except Exception as e:
                logger.error(f"Error with vision analysis for {file}: {str(e)}")
            
            if match_found or not results:  # Include first image's analysis even if no match
                results.append(result_entry)
        
        return "".join(results) if results else "No matching content found"
    except Exception as e:
        logger.error(f"Error in search_images: {str(e)}")
        return f"Error searching images: {str(e)}"


# � Detect objects and people in images
def detect_objects_and_people(query: str = "all") -> str:
    """Analyze all images in data/images to detect and count people, objects, and other elements."""
    results = []
    
    try:
        img_dir = "data/images"
        if not os.path.exists(img_dir):
            return "Images directory not found"
        
        images = [f for f in os.listdir(img_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
        if not images:
            return "No images available in data/images/"
        
        for file in sorted(images):
            file_path = os.path.join(img_dir, file)
            
            try:
                # Use vision analysis to detect objects and people
                analysis = _analyze_image_with_vision(file_path)
                result = f"\n📷 {file}:\n{analysis}"
                
                # Filter results if specific query provided
                if query.lower() != "all" and query.lower() not in analysis.lower():
                    continue
                
                results.append(result)
            except Exception as e:
                logger.error(f"Error analyzing {file}: {str(e)}")
                results.append(f"\n📷 {file}: Error - {str(e)}")
        
        if not results and query.lower() != "all":
            return f"No images found matching '{query}'. Run with 'all' to see all analyses."
        
        return "".join(results) if results else "No images available"
    except Exception as e:
        logger.error(f"Error in detect_objects_and_people: {str(e)}")
        return f"Error detecting objects: {str(e)}"


# �🔗 Extract links
def extract_links(text: str) -> str:
    """Extract URLs from the given text."""
    try:
        links = re.findall(r'https?://\S+', text)
        return "\n".join(links) if links else "No links found"
    except Exception as e:
        logger.error(f"Error in extract_links: {str(e)}")
        return f"Error extracting links: {str(e)}"
