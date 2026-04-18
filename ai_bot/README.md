# AI Bot Module

Core agent module for the AI Assistant application. Provides the Gemini-powered agent with document search, image OCR, and link extraction capabilities.

## Overview

The `ai_bot` module encapsulates the Google ADK (Agent Development Kit) agent initialization, configuration, and query interface. It serves as the brain of the AI Assistant, handling natural language queries and orchestrating tool calls.

## Module Structure

```
ai_bot/
├── __init__.py           # Module initialization
├── agent.py              # Main agent configuration and query interface
└── aiquery/
    └── tmp/              # ADK temporary configuration files
        └── aiquery/
            └── root_agent.yaml  # Agent configuration
```

## Components

### agent.py

The main module file containing agent initialization and query execution.

**Key Exports:**
- `query_agent(query: str, user_id: str = 'web_user', session_id: str = 'web_session') -> str`
  - Async function to query the agent
  - Returns assistant response as string
  - Automatically handles event extraction and session management

**Agent Configuration:**
- **Model**: `gemini-2.5-flash` (Google's fastest multimodal model)
- **Name**: `root_agent`
- **Tools**: `search_pdfs`, `search_images`, `extract_links`

**System Instruction:**
```
A helpful assistant that searches local PDFs and images using provided tools.
When users ask for information, use the search_pdfs tool to find relevant content.
For image-related queries, use search_images with OCR.
Always extract links when they appear in search results.
```

## Usage

### Direct Module Import

```python
from ai_bot.agent import query_agent

# Query the agent
response = await query_agent("What technical skills are mentioned?")
print(response)
```

### From Main Application

The FastAPI server in `main.py` uses this module:

```python
from ai_bot.agent import query_agent

@app.post("/ask")
async def ask(q: Query):
    response = await query_agent(q.query)
    return {"response": response}
```

### Web UI

Access the interactive development interface:
```bash
adk web --verbose --port 8000 ai_bot
# Navigate to http://127.0.0.1:8000/dev-ui/?app=ai_bot
```

## Architecture

### Agent Initialization

The agent is initialized with:
1. **Model**: Gemini 2.5 Flash (automatic function calling enabled)
2. **Tools**: Three callable tools for information retrieval
3. **Runner**: InMemoryRunner for proper context management
4. **Session**: Automatic conversation session handling

### Query Flow

```
user query
    ↓
query_agent() wrapper
    ↓
InMemoryRunner.run_debug()
    ↓
ADK Agent processes query
    ↓
Agent evaluates tools needed
    ↓
Tool execution (search_pdfs, search_images, extract_links)
    ↓
Response generation
    ↓
Event extraction
    ↓
Return response to caller
```

### Event Handling

The agent produces ADK Event objects. The module extracts text using:
- `_extract_event_text(event)` - Parses event.content.parts structure
- Handles multiple event types (assistant response, tool calls, etc.)
- Returns cleaned text response

## Tools

### search_pdfs(query: str)

Searches documents in `data/pdfs/` directory.

**Supports:**
- PDF files (.pdf)
- Apple Pages (.pages)

**Returns:**
- Matching content excerpts with source file and page number
- List of available documents if no matches found

**Example:**
```
Query: "What technical skills are mentioned?"
Response: "Found match in Resume-Gaurav-k.pdf page 1:
Python, Golang, Kubernetes, AWS, Azure, NLP, OpenAI integration..."
```

### search_images(query: str)

Performs OCR-based search on images in `data/images/`.

**Supports:**
- PNG, JPG, JPEG, GIF, BMP

**Returns:**
- Text extracted from images matching the query

### extract_links(text: str)

Extracts URLs from provided text.

**Returns:**
- List of HTTP/HTTPS links found

## Integration Points

### FastAPI Server ([main.py](../main.py))

```python
from ai_bot.agent import query_agent

@app.post("/ask")
async def ask(q: Query):
    response = await query_agent(q.query)
    return {"response": response}
```

### Development Tools ([tools.py](../tools.py))

The agent calls tools defined in the parent directory:
- `search_pdfs()` - Tool implementation
- `search_images()` - Tool implementation
- `extract_links()` - Tool implementation

## Configuration

### Model Selection

Change the model in `agent.py`:
```python
_root_agent = Agent(
    model='gemini-2.5-flash',  # Change this
    ...
)
```

Available models:
- `gemini-2.5-flash` - Fastest, best for streaming
- `gemini-2.0-flash` - Balanced performance
- `gemini-pro` - High capability

### System Instruction

Customize agent behavior by editing the instruction parameter:
```python
instruction="""
Your custom system prompt here.
Define how the agent should behave and interact.
"""
```

### Session Management

Configure session behavior in `query_agent()`:
```python
async def query_agent(
    query: str,
    user_id: str = 'web_user',      # Change this
    session_id: str = 'web_session'  # Or this
):
    ...
```

## Error Handling

The agent includes comprehensive error handling:

1. **Tool Errors**: If a tool fails, returns error message instead of crashing
2. **API Errors**: Implements exponential backoff retry for 503/429 errors
3. **Event Extraction**: Gracefully handles malformed events
4. **Logging**: All errors logged for debugging

## Performance Considerations

### Streaming
- Agent uses event streaming for real-time responses
- Dev UI shows events as they arrive
- No buffering - immediate feedback

### Session Management
- InMemoryRunner maintains session state
- Conversation context preserved within session
- Multiple users can have independent sessions

### Async Design
- All agent queries are async
- Non-blocking I/O for tool execution
- Scalable to many concurrent queries

## Running the AI Bot

### Prerequisites

1. **Correct Folder Location**
   ```bash
   cd /Users/gaurav/ai-assistant
   ```
   All commands must run from the **root project directory** (not from inside `ai_bot/`)

2. **Virtual Environment Active**
   ```bash
   source .venv/bin/activate
   ```
   Check activation: `which python` should show `.venv/bin/python`

3. **API Key Set**
   ```bash
   export GOOGLE_API_KEY="your-gemini-api-key"
   ```

### Method 1: ADK Web UI (Recommended)

**Best for**: Interactive testing, visual debugging, development

#### Step 1: Check Port Availability
```bash
# Check if port 8000 is available
lsof -i :8000
```

If port 8000 is in use:
```bash
# Kill process on port 8000
kill -9 $(lsof -t -i:8000)

# Or use a different port (see "Port Conflicts" section)
```

#### Step 2: Start the AI Bot Web Server
```bash
source .venv/bin/activate
adk web --verbose --port 8000 ai_bot
```

**Output should show:**
```
✓ Running ADK web server
✓ Server started at http://127.0.0.1:8000
✓ Agent app=ai_bot loaded
```

#### Step 3: Test in Browser

Open browser and navigate to:
```
http://127.0.0.1:8000/dev-ui/?app=ai_bot
```

You should see:
- Development UI interface
- Message input box
- Chat history area

#### Step 4: Send Test Query

1. Type in the message box: `Search for technical skills in resume`
2. Click "Send" or press Enter
3. Watch the agent process:
   - Agent calls `search_pdfs()` tool
   - Returns relevant excerpts
   - Displays in chat

### Method 2: FastAPI Server + Browser Testing

**Best for**: REST API testing, production-like environment

#### Step 1: Kill Any Existing Process
```bash
# Kill any Python server on port 8001
kill -9 $(lsof -t -i:8001)

# Or use different port
```

#### Step 2: Start FastAPI Server
```bash
source .venv/bin/activate
python3 -m uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

**Output should show:**
```
INFO:     Uvicorn running on http://127.0.0.1:8001
INFO:     Application startup complete
```

#### Step 3: Test API with curl
```bash
curl -X POST http://127.0.0.1:8001/ask \
  -H "Content-Type: application/json" \
  -d '{"query":"What are the main skills?"}'
```

**Expected Response:**
```json
{
  "response": "Found in Resume-Gaurav-k.pdf page 1: Python, Golang, Kubernetes, AWS..."
}
```

#### Step 4: Test in Browser (Swagger Docs)

Navigate to:
```
http://127.0.0.1:8001/docs
```

- Click "Try it out" on the `/ask` endpoint
- Enter query in the request body
- Click "Execute"
- See response below

### Method 3: Direct Python Testing (Minimal)

**Best for**: Quick debugging, unit testing

#### From Project Root
```bash
cd /Users/gaurav/ai-assistant
source .venv/bin/activate
```

#### Create test_agent.py
```bash
cat > test_agent.py << 'EOF'
import asyncio
from ai_bot.agent import query_agent

async def test():
    print("Testing AI Bot agent...\n")
    
    # Test 1: Basic search
    print("Test 1: Search for skills")
    response = await query_agent("What technical skills are mentioned?")
    print(f"Response: {response}\n")
    
    # Test 2: Resume search
    print("Test 2: Search resume")
    response = await query_agent("What companies are listed?")
    print(f"Response: {response}\n")
    
    # Test 3: Image search
    print("Test 3: Search images")
    response = await query_agent("Find text in images")
    print(f"Response: {response}\n")
    
    print("All tests completed!")

asyncio.run(test())
EOF
```

#### Run the Test
```bash
python3 test_agent.py
```

### Port Conflicts & Management

#### Understanding Port Usage

**Default Ports:**
- ADK Web UI: `8000`
- FastAPI Server: `8001`
- Alternative ports: `8002`, `8003`, etc.

#### Check Port Status
```bash
# Check specific port
lsof -i :8000

# Check all Python processes
ps aux | grep python

# Check all listening ports
lsof -i -P -n | grep LISTEN
```

#### Kill Processes by Port
```bash
# Kill process on port 8000
kill -9 $(lsof -t -i:8000)

# Kill process on port 8001
kill -9 $(lsof -t -i:8001)

# Force kill (if above doesn't work)
fuser -k 8000/tcp
```

#### Use Different Ports

**ADK Web with different port:**
```bash
adk web --verbose --port 8005 ai_bot
# Then access: http://127.0.0.1:8005/dev-ui/?app=ai_bot
```

**FastAPI with different port:**
```bash
python3 -m uvicorn main:app --host 127.0.0.1 --port 8006 --reload
# Then access: http://127.0.0.1:8006/docs
```

#### Background Process (Advanced)

Run server in background:
```bash
# Using nohup
nohup python3 -m uvicorn main:app --host 127.0.0.1 --port 8001 > server.log 2>&1 &

# Check status
cat server.log

# Kill background process
kill %1  # or use job number from jobs command
```

### Troubleshooting Startup Issues

#### Error: "Port already in use"
```
OSError: [Errno 48] Address already in use
```

**Solution:**
```bash
# Find and kill process on the port
lsof -i :8000
kill -9 <PID>

# Or use different port
adk web --verbose --port 8002 ai_bot
```

#### Error: "Virtual environment not activated"
```
command not found: adk
```

**Solution:**
```bash
# Activate virtual environment
source .venv/bin/activate

# Verify activation (should show .venv in path)
which python
# Output: /Users/gaurav/ai-assistant/.venv/bin/python
```

#### Error: "GOOGLE_API_KEY not set"
```
No API key provided
```

**Solution:**
```bash
export GOOGLE_API_KEY="your-actual-api-key-here"

# Verify it's set
echo $GOOGLE_API_KEY
```

#### Error: "Module not found"
```
ModuleNotFoundError: No module named 'google'
```

**Solution:**
```bash
# From project root, reinstall dependencies
source .venv/bin/activate
pip install -r requirements.txt
```

#### Error: "Working from wrong directory"
```
FileNotFoundError: data/pdfs/ not found
```

**Solution:**
```bash
# Must be in project root directory
cd /Users/gaurav/ai-assistant

# Verify correct location
pwd
# Output: /Users/gaurav/ai-assistant

# Check data directory exists
ls -la data/pdfs/
```

### Testing Checklist

#### Before Testing
- [ ] Terminal is in `/Users/gaurav/ai-assistant`
- [ ] Virtual environment activated (`source .venv/bin/activate`)
- [ ] Google API key set (`export GOOGLE_API_KEY=...`)
- [ ] Port not in use (`lsof -i :8000`)
- [ ] Data directories exist (`data/pdfs/`, `data/images/`)

#### During Testing (ADK Web UI)
- [ ] Web server started successfully
- [ ] Browser shows dev-ui interface
- [ ] Message input field is visible
- [ ] Can type and send queries

#### During Testing (FastAPI)
- [ ] Server shows "Application startup complete"
- [ ] Can access Swagger docs at `/docs`
- [ ] Can POST to `/ask` endpoint
- [ ] Receives valid JSON response

#### After Testing
- [ ] Server responds consistently
- [ ] Tools execute without errors
- [ ] Response text is meaningful
- [ ] No stream crashes

### Development

### Testing the Agent

Direct test without FastAPI:
```python
import asyncio
from ai_bot.agent import query_agent

async def test():
    response = await query_agent("test query")
    print(response)

asyncio.run(test())
```

### Debug Mode

The agent runs with `verbose=False` by default. Enable debug output:
```python
# In agent.py, change:
events = await runner.run_debug(query, ..., verbose=True)
```

### Event Inspection

Monitor event flow in dev-ui:
- Click on messages to see raw events
- Check event types and content
- Verify tool execution order

## Dependencies

### Python Packages
- `google-adk` - Agent Development Kit
- `google-generativeai` - Gemini API
- Related to parent dependencies in [requirements.txt](../requirements.txt)

### Google API
- Gemini 2.5 Flash model
- Automatic function calling enabled
- Event streaming support

## Troubleshooting

### "No such file or directory: root_agent.yaml"
**Solution**: The ADK configuration is auto-generated in `aiquery/tmp/`. Ensure write permissions:
```bash
chmod -R 755 ai_bot/aiquery/
```

### Agent doesn't find tools
**Solution**: Ensure tools are imported correctly in agent.py:
```python
from tools import search_pdfs, search_images, extract_links
```

### Response is empty
**Solution**: Check event extraction. Tools may have failed silently. Look at logs for tool execution details.

### "stream has ended unexpectedly"
**Solution**: Tool crashed without error handling. This should not happen with current code, but check tool implementations in [tools.py](../tools.py).

## Future Enhancements

1. **Multi-turn Conversations**: Maintain conversation history
2. **Custom Tools**: Add specialized search tools
3. **Fine-tuning**: Adapt agent to domain-specific queries
4. **Caching**: Cache search results for performance
5. **Analytics**: Track query patterns and tool usage
6. **Context Awareness**: Improve document understanding

## API Reference

### query_agent()

```python
async def query_agent(
    query: str,
    user_id: str = 'web_user',
    session_id: str = 'web_session'
) -> str
```

**Parameters:**
- `query` (str): The user's natural language query
- `user_id` (str): User identifier for logging (default: 'web_user')
- `session_id` (str): Session identifier for conversation context (default: 'web_session')

**Returns:**
- `str`: The agent's response as plain text

**Raises:**
- Exceptions are caught and logged; function returns error message string

**Example:**
```python
response = await query_agent("Search for Python skills in the resume")
# Returns: "Found in Resume-Gaurav-k.pdf..."
```

## Contributing

To extend the AI Bot:

1. **Add Tools**: Implement new tools in [tools.py](../tools.py)
2. **Update Agent**: Import new tools in `agent.py` and add to tools list
3. **Test**: Query with dev-ui to verify functionality
4. **Document**: Update this README with new capabilities

## License

Proprietary - Internal use only

## Support

For issues with the AI Bot module:
1. Check error logs in console output
2. Test individual tools with [tools.py](../tools.py)
3. Verify data directories exist: `data/pdfs/`, `data/images/`
4. Enable verbose logging in `agent.py` for debugging
5. Check Google API key is set: `echo $GOOGLE_API_KEY`
