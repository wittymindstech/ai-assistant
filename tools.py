import os
import re
import logging
import json
import zipfile
import base64
import tempfile
from io import BytesIO
from pathlib import Path
from typing import List

import boto3
from botocore.exceptions import ClientError
from PIL import Image
import pytesseract
from pypdf import PdfReader
import google.genai as genai

from config import Config

ROOT_DIR = Path(__file__).resolve().parent
DATA_ROOT = ROOT_DIR / "data" if (ROOT_DIR / "data").exists() else ROOT_DIR.parent / "data"
PDFS_DIR = DATA_ROOT / "pdfs"
IMAGES_DIR = DATA_ROOT / "images"

logger = logging.getLogger(__name__)

# S3 client (uses IAM role or environment credentials)
_s3 = boto3.client('s3') if Config.S3_BUCKET else None


def _list_s3_objects(prefix: str) -> List[dict]:
    if Config.S3_BUCKET and _s3:
        paginator = _s3.get_paginator('list_objects_v2')
        objs = []
        try:
            for page in paginator.paginate(Bucket=Config.S3_BUCKET, Prefix=prefix):
                for item in page.get('Contents', []):
                    objs.append(item)
        except ClientError as e:
            logger.error(f"S3 list error for prefix {prefix}: {e}")
        return objs

    search_dir = PDFS_DIR if prefix.startswith('pdfs') else IMAGES_DIR if prefix.startswith('images') else DATA_ROOT / prefix
    if not search_dir.exists():
        return []

    objs = []
    for file_path in sorted(search_dir.rglob('*')):
        if file_path.is_file():
            key = str(file_path.relative_to(DATA_ROOT)).replace(os.sep, '/')
            objs.append({'Key': key})
    return objs


def _get_s3_object_bytes(key: str) -> bytes:
    if Config.S3_BUCKET and _s3:
        try:
            resp = _s3.get_object(Bucket=Config.S3_BUCKET, Key=key)
            return resp['Body'].read()
        except ClientError as e:
            logger.error(f"Failed to get S3 object {key}: {e}")
            raise

    if key.startswith('s3://'):
        key = key.split('s3://', 1)[-1]

    local_path = DATA_ROOT / key
    if local_path.exists():
        return local_path.read_bytes()

    raise RuntimeError("S3 is not configured. Set S3_BUCKET in environment or provide local data files.")


def _extract_text_from_pages_bytes(data: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(data), 'r') as pages_zip:
            try:
                if 'index.json' in pages_zip.namelist():
                    with pages_zip.open('index.json') as f:
                        parsed = json.load(f)
                        if isinstance(parsed, dict) and 'documentMetadata' in parsed:
                            return json.dumps(parsed, indent=2)[:2000]
            except Exception:
                pass

            text_content = []
            for name in pages_zip.namelist():
                if name.endswith('.txt'):
                    try:
                        with pages_zip.open(name) as f:
                            text_content.append(f.read().decode('utf-8', errors='ignore'))
                    except Exception:
                        continue

            if text_content:
                return '\n'.join(text_content)[:2000]

            return f"Pages file detected. Files in archive: {', '.join(pages_zip.namelist()[:5])}"
    except Exception as e:
        logger.error(f"Error extracting from Pages bytes: {str(e)}")
        return f"Error reading Pages file: {str(e)}"


def _get_available_documents_s3() -> str:
    objs = _list_s3_objects(Config.S3_PREFIX_PDFS)
    if not objs:
        return "No documents available in S3 pdfs/"
    file_info = [os.path.basename(o.get('Key', '')) for o in objs]
    return "Available documents: " + ", ".join(file_info[:50])


def search_pdfs(query: str) -> str:
    results = []
    try:
        objs = _list_s3_objects(Config.S3_PREFIX_PDFS)
        if not objs:
            return "No documents available in S3 pdfs/"

        for o in sorted(objs, key=lambda x: x.get('Key', '')):
            key = o.get('Key')
            if not key:
                continue
            name = os.path.basename(key)
            ext = os.path.splitext(name)[1].lower()

            if ext == '.pdf':
                try:
                    data = _get_s3_object_bytes(key)
                    with BytesIO(data) as b:
                        reader = PdfReader(b)
                        for page_num, page in enumerate(reader.pages):
                            text = page.extract_text() or ""
                            if query.lower() in text.lower():
                                results.append(f"[PDF: {name}, page {page_num+1}] {text[:500]}")
                except Exception as e:
                    logger.error(f"Error reading S3 PDF {key}: {e}")
                    continue

            elif ext == '.pages' or key.endswith('.pages'):
                try:
                    data = _get_s3_object_bytes(key)
                    content = _extract_text_from_pages_bytes(data)
                    if query.lower() in content.lower():
                        results.append(f"[Pages: {name}] {content[:500]}")
                except Exception as e:
                    logger.error(f"Error reading S3 Pages file {key}: {e}")
                    continue

        if results:
            return "\n\n".join(results)
        else:
            available = _get_available_documents_s3()
            return f"No matching content found for '{query}'.\n{available}"
    except Exception as e:
        logger.error(f"Error in search_pdfs (S3): {str(e)}")
        return f"Error searching documents: {str(e)}"


def _analyze_image_with_vision_bytes(image_bytes: bytes, mime_type: str) -> str:
    try:
        image_data = base64.standard_b64encode(image_bytes).decode('utf-8')
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


def search_images(query: str) -> str:
    results = []
    try:
        objs = _list_s3_objects(Config.S3_PREFIX_IMAGES)
        if not objs:
            return "No images available in S3 images/"

        for o in sorted(objs, key=lambda x: x.get('Key', '')):
            key = o.get('Key')
            if not key:
                continue
            name = os.path.basename(key)
            result_entry = f"\n📷 {name}:\n"
            match_found = False

            try:
                data = _get_s3_object_bytes(key)
                img = Image.open(BytesIO(data))
                ocr_text = pytesseract.image_to_string(img)
                if ocr_text and query.lower() in ocr_text.lower():
                    result_entry += f"  [OCR Text Match] {ocr_text[:300]}\n"
                    match_found = True
            except Exception as e:
                logger.error(f"Error running OCR on S3 image {key}: {e}")

            try:
                ext = os.path.splitext(name)[1].lower()
                mime_map = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.gif': 'image/gif', '.bmp': 'image/bmp', '.webp': 'image/webp'}
                mime = mime_map.get(ext, 'image/jpeg')
                vision_analysis = _analyze_image_with_vision_bytes(data, mime)
                result_entry += f"  [Vision Analysis]\n{vision_analysis}\n"
                if query.lower() in vision_analysis.lower():
                    match_found = True
            except Exception as e:
                logger.error(f"Error with vision analysis for S3 image {key}: {e}")

            if match_found or not results:
                results.append(result_entry)

        if results:
            return "\n\n".join(results)
        else:
            return "No matching images found"
    except Exception as e:
        logger.error(f"Error in search_images (S3): {str(e)}")
        return f"Error searching images: {str(e)}"


def _analyze_image_with_vision(image_path: str) -> str:
    try:
        # Compatibility shim: support local path or s3://bucket/key
        if image_path.startswith('s3://') and _s3:
            # image_path format: s3://bucket/key or s3://key
            parts = image_path.split('s3://')[-1]
            key = parts.split('/', 1)[1] if '/' in parts else parts
            data = _get_s3_object_bytes(key)
            return _analyze_image_with_vision_bytes(data, 'image/jpeg')
        elif os.path.exists(image_path):
            with open(image_path, 'rb') as f:
                data = f.read()
                return _analyze_image_with_vision_bytes(data, 'image/jpeg')
        else:
            return "Image not found"
    except Exception as e:
        logger.error(f"Failed to analyze image {image_path}: {e}")
        return "Analysis failed"


def detect_objects_and_people(query: str = "all") -> str:
    results = []
    try:
        objs = _list_s3_objects(Config.S3_PREFIX_IMAGES)
        if not objs:
            return "No images available in S3 images/"

        for o in sorted(objs, key=lambda x: x.get('Key', '')):
            key = o.get('Key')
            if not key:
                continue
            name = os.path.basename(key)
            try:
                data = _get_s3_object_bytes(key)
                analysis = _analyze_image_with_vision_bytes(data, 'image/jpeg')
                if query.lower() != 'all' and query.lower() not in analysis.lower():
                    continue
                results.append(f"\n📷 {name}:\n{analysis}")
            except Exception as e:
                logger.error(f"Error analyzing {key}: {str(e)}")
                results.append(f"\n📷 {name}: Error - {str(e)}")

        if not results and query.lower() != 'all':
            return f"No images found matching '{query}'. Run with 'all' to see all analyses."

        return "".join(results) if results else "No images available"
    except Exception as e:
        logger.error(f"Error in detect_objects_and_people: {str(e)}")
        return f"Error detecting objects: {str(e)}"


def extract_links(text: str) -> str:
    try:
        links = re.findall(r'https?://\S+', text)
        return "\n".join(links) if links else "No links found"
    except Exception as e:
        logger.error(f"Error in extract_links: {str(e)}")
        return f"Error extracting links: {str(e)}"
