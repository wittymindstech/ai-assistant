# AI Assistant Bot

An intelligent document search and analysis agent powered by Google's Agent Development Kit (ADK) and Gemini 2.5 Flash.

## Features

- **Document Search**: Search through PDF documents and Apple Pages files in `data/pdfs/`
- **OCR & Image Analysis**: Extract text from images in `data/images/` using pytesseract
- **Link Extraction**: Automatically detect and extract URLs from text
- **Web UI**: Interactive development UI at `http://127.0.0.1:8000/dev-ui/`
- **REST API**: FastAPI endpoint for programmatic access

## Architecture

```
ai-assistant/
├── ai_bot/                    # AI agent module
│   ├── agent.py              # Main agent configuration
│   └── __init__.py
├── data/
│   ├── pdfs/                 # PDF and .pages documents
│   └── images/               # Images for OCR
├── tools.py                  # Search tools (PDFs, images, links)
├── main.py                   # FastAPI server
└── requirements.txt          # Dependencies
```

## Installation

### Prerequisites
- Python 3.9+
- Virtual environment manager (venv)
- Tesseract OCR (for image processing)

### Setup

1. **Clone and navigate to the project:**
```bash
cd /Users/gaurav/ai-assistant
```

2. **Create and activate virtual environment:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set API key:**
```bash
export GOOGLE_API_KEY="your-api-key-here"
```

## Running the Application

### Option 1: ADK Web Server (Recommended)
Interactive web UI with dev tools:
```bash
source .venv/bin/activate
adk web --verbose --port 8000 ai_bot
```
Then visit: `http://127.0.0.1:8000/dev-ui/?app=ai_bot`

### Option 2: FastAPI Server
REST API only:
```bash
source .venv/bin/activate
python3 -m uvicorn main:app --host 127.0.0.1 --port 8001
```

## API Usage

### Query the Agent
```bash
curl -X POST http://127.0.0.1:8001/ask \
  -H "Content-Type: application/json" \
  -d '{"query":"search for technical skills in resume"}'
```

**Response:**
```json
{
  "response": "The resume shows proficiency in Python, Golang, Kubernetes, AWS, Azure, NLP, OpenAI..."
}
```

## Available Tools

### 1. search_pdfs(query: str)
Searches through documents in `data/pdfs/`
- **Supports**: PDF files (.pdf), Apple Pages (.pages)
- **Returns**: Matching content with source file and location

### 2. search_images(query: str)
Performs OCR on images in `data/images/`
- **Supports**: PNG, JPG, JPEG, GIF, BMP
- **Returns**: Text extracted from matching images

### 3. extract_links(text: str)
Extracts URLs from text
- **Returns**: List of HTTP/HTTPS links found

## Configuration

### Agent Settings
Edit `ai_bot/agent.py`:
- **Model**: `gemini-2.5-flash` (default)
- **Name**: `root_agent`
- **System Instruction**: Customizable prompt for agent behavior

### Data Directories
- **PDFs**: Place documents in `data/pdfs/` (supports .pdf and .pages)
- **Images**: Place images in `data/images/` for OCR analysis

## Development

### Directory Structure
```
ai_bot/
├── __init__.py
├── agent.py          # Agent initialization and query interface
└── aiquery/
    └── tmp/          # Temporary ADK configuration files
```

### Key Files

**ai_bot/agent.py**
- Initializes the Gemini agent with tools
- Exports `query_agent()` async function
- Handles event extraction from ADK runner

**tools.py**
- `search_pdfs()`: PDF/Pages document search
- `search_images()`: OCR-based image search
- `extract_links()`: URL extraction

**main.py**
- FastAPI server setup
- `/ask` POST endpoint for REST API queries
- CORS middleware configuration

## Troubleshooting

### Issue: "Stream has ended unexpectedly"
**Solution**: Tools have built-in error handling. Ensure data directories exist:
```bash
mkdir -p data/pdfs data/images
```

### Issue: "Model is currently experiencing high demand (503)"
**Solution**: This is temporary. The agent retries automatically up to 4 times with exponential backoff.

### Issue: `.pages` file not extracting text
**Note**: .pages files are ZIP archives. Text extraction attempts to read internal JSON structures. Full content extraction may require specialized libraries.

## Environment Variables

```bash
# Google API Key (required)
export GOOGLE_API_KEY="your-gemini-api-key"
```

## Performance Notes

- **Automatic Retries**: 503/429 errors retry up to 4 times with exponential backoff
- **Session Management**: ADK manages conversation sessions automatically
- **Event Streaming**: Dev UI streams events in real-time
- **Error Recovery**: Tools gracefully handle missing files and invalid formats

## Dependencies

- **google-adk**: Agent Development Kit for building AI agents
- **fastapi**: Web framework
- **pydantic**: Data validation
- **pypdf**: PDF text extraction
- **pillow**: Image processing
- **pytesseract**: OCR engine

## License

Proprietary - Internal use only

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review tool error logs in console output
3. Verify data/pdfs and data/images directories contain valid files
