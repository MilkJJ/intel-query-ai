# Phase 7: End-to-End Testing & Validation

## Quick Start Checklist

### ✅ Backend Setup
- [ ] Python 3.10+ installed
- [ ] All dependencies installed: `pip install -r python-backend/requirements.txt`
- [ ] Backend can start without errors

### ✅ Frontend Setup
- [ ] Node.js installed
- [ ] Dependencies installed: `npm install` (in frontend directory)
- [ ] Frontend dev server ready

### ✅ LLM Model Setup (Critical for Phase 5)
To use LLM-generated insights instead of heuristics, you MUST download a model file.

**Option 1: TinyLlama (Recommended - 4GB)**
```bash
# Create models directory
mkdir -p python-backend/models

# Download TinyLlama 1.1B (fastest, works on most systems)
# Download from: https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF
# Or use this direct link:
cd python-backend/models
wget https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
```

**Option 2: Mistral 7B (Better quality - 7B, ~16GB)**
```bash
# If you have GPU with 8GB+ VRAM
wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.1-GGUF/resolve/main/mistral-7b-instruct-v0.1.Q4_K_M.gguf
```

**After downloading:**
- Restart the backend
- Check logs for "✓ Llama.cpp model loaded successfully"

---

## Test Scenarios

### Scenario 1: Verify Backend is Running
1. Open terminal, navigate to `python-backend/`
2. Run: `python main.py`
3. Check for these log messages:
   ```
   [Phase 2] Starting gRPC services...
   ✓ gRPC services initialized successfully
   [Phase 4] Initializing LLM service...
   ✓ LLM service READY (model loaded)  ← This is what you want!
   ```
4. If you see "LLM service in HEURISTIC MODE (model not available)" → Download a model file

### Scenario 2: Verify Frontend is Running
1. Open new terminal
2. Navigate to project root (intel-query-ai/)
3. Run: `npm run dev`
4. Open http://localhost:5173 in browser
5. Should see chat interface

### Scenario 3: Test Full Pipeline (Transcription Only)
1. Upload a video file (.mp4, .avi, .mov, etc.)
2. Send query: "Transcribe the video"
3. Expected response: Full transcript
4. Check for: `[transcription_agent]` in response

### Scenario 4: Test Vision Analysis
1. Upload video
2. Send query: "What objects are shown?"
3. Expected response: List of detected objects
4. Check for: `[vision_agent]` in response

### Scenario 5: Test LLM Integration (Critical)
1. **Make sure you have downloaded a model file** (see LLM Model Setup above)
2. Upload video
3. Send query: "Summarize this video"
4. Expected response: LLM-generated summary
5. Check backend logs for:
   - `Using LLM service for summary generation` (if model loaded)
   - OR `LLM service unavailable, using heuristic summary` (if no model)

### Scenario 6: Test PDF Report Generation (Phase 5)
1. Upload video
2. Send query: "Generate a PDF report"
3. Expected: PDF downloads with **9-section structure**:
   - Title + Metadata
   - TL;DR
   - Executive Summary (LLM)
   - Key Topics (LLM)
   - Scene Analysis
   - Object Detection Results (table)
   - Graph Analysis (if applicable)
   - Key Insights (LLM)
   - Conclusion (LLM)

4. **If you see only transcript content**: LLM is not activated
   - Check backend logs for "LLM service in HEURISTIC MODE"
   - Download a model file and restart backend

### Scenario 7: Test PPT Report Generation
1. Upload video
2. Send query: "Create a PowerPoint presentation"
3. Expected: PPT downloads with **6 slides**:
   - Title slide
   - Executive Summary (LLM)
   - Key Topics (LLM)
   - Objects Detected
   - Key Insights (LLM)
   - Conclusion (LLM)

---

## Debugging Checklist

### Issue: "LLM service in HEURISTIC MODE"
**Solution:**
1. Download a .gguf model file (see LLM Model Setup)
2. Place in `python-backend/models/`
3. Restart backend
4. Check logs for "✓ Llama.cpp model loaded successfully"

### Issue: "Request failed: Backend not responding"
**Solution:**
1. Make sure backend is running: `python main.py` in `python-backend/`
2. Check if port 8000 is in use
3. Try: `lsof -i :8000` to see what's using the port

### Issue: "PDF shows only transcript"
**Solution:**
1. This means LLM isn't being used
2. Check backend logs for LLM status
3. Download and place model file
4. Restart backend

### Issue: "gRPC services failed to start"
**Solution:**
1. Check if proto files are compiled: `ls python-backend/services/grpc_servers/`
2. Should have `*_pb2.py` and `*_pb2_grpc.py` files
3. If missing, run: `python -m grpc_tools.protoc -I proto/ --python_out=services/grpc_servers/ --grpc_python_out=services/grpc_servers/ proto/*.proto`

---

## Expected Outputs

### Good Log Output (Backend Starting)
```
════════════════════════════════════════════════════════════════════════════════
INTEL QUERY AI - BACKEND STARTUP
════════════════════════════════════════════════════════════════════════════════

[Phase 2] Starting gRPC services...
✓ gRPC services initialized successfully
  - transcription_service: ready
  - vision_service: ready
  - generation_service: ready

[Phase 4] Initializing LLM service...
✓ LLM service READY (model loaded)
  Model: tinyllama
  Mode: llm (full reasoning enabled)

════════════════════════════════════════════════════════════════════════════════
Backend ready for requests!
════════════════════════════════════════════════════════════════════════════════
```

### Bad Log Output (No Model)
```
[Phase 4] Initializing LLM service...
ℹ LLM service in HEURISTIC MODE (model not available)
  To use LLM: download a GGUF model and place in ./models/
  Recommended: https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF
```

---

## Performance Targets

- **Transcription**: < 5 seconds for 30-second video
- **Vision Analysis**: < 10 seconds
- **LLM Insights**: < 5 seconds per insight (TinyLlama), < 30 seconds (Mistral)
- **PDF Generation**: < 2 seconds
- **PPT Generation**: < 2 seconds

---

## Testing Commands

### Test Backend Health
```bash
curl http://localhost:8000/
```

### Test Backend Status
```bash
curl http://localhost:8000/status
```

### Test with Sample Video (from CLI)
```bash
curl -X POST http://localhost:8000/query \
  -F "file=@/path/to/video.mp4" \
  -F "query=Summarize this video"
```

---

## Next Steps After Testing

- [ ] All scenarios pass
- [ ] LLM is showing in logs as "READY"
- [ ] PDF reports show 9-section structure with LLM insights
- [ ] PPT reports show 6 slides with LLM insights
- [ ] No transcript dumps in reports (only insights)
- [ ] Error handling works (no crashes on bad input)
