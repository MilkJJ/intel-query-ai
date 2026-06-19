# Why PDF Shows Only Transcript & How to Fix It

## The Issue

You're seeing **transcript-only content in the PDF** because the LLM service is running in **HEURISTIC MODE** instead of **LLM MODE**. This happens when:

- ❌ No GGUF model file is found
- ❌ Model file can't be loaded
- ❌ `llama-cpp-python` module isn't installed

The system **gracefully falls back** to heuristic generation, but you won't get the 9-section insight-driven PDF that Phase 5 provides.

---

## Solution: Enable LLM Mode in 3 Steps

### Step 1: Check Current Status

Run the debug script to see what's happening:

```bash
cd python-backend
python debug_phase7.py
```

Look for this section in the output:

**If you see this:**
```
[6] Checking LLM service initialization...
  ⚠ LLM service in HEURISTIC MODE
    Model not found, but service enabled
    To enable LLM: download a .gguf model file
```

→ **This is why you're getting transcript-only PDFs!**

**If you see this:**
```
[6] Checking LLM service initialization...
  ✓ LLM service READY
    Model: tinyllama
    Mode: LLM (full reasoning)
```

→ **LLM is enabled, something else is wrong**

---

### Step 2: Download a Model

You need ONE of these model files. Choose based on your system:

#### **Option A: TinyLlama (Recommended - Fastest)**
- **Size:** ~4 GB (compressed: ~1.5 GB)
- **Speed:** 5-10 seconds per insight
- **Quality:** Good enough for summaries
- **RAM:** 6 GB minimum
- **Where:** https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF

**Steps:**
```bash
# 1. Create models directory
cd python-backend
mkdir -p models

# 2. Download using wget
cd models
wget https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf

# OR download using PowerShell (Windows)
# Save the URL in your browser:
# https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
```

#### **Option B: Mistral 7B (Better Quality)**
- **Size:** ~15 GB  
- **Speed:** 10-30 seconds per insight
- **Quality:** Much better reasoning
- **RAM:** 16 GB minimum
- **GPU:** 8GB VRAM recommended
- **Where:** https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.1-GGUF

```bash
cd python-backend/models
wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.1-GGUF/resolve/main/mistral-7b-instruct-v0.1.Q4_K_M.gguf
```

**Using Browser (Easier):**
1. Go to: https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF
2. Click on the `.gguf` file
3. Click "Download"
4. Move to `python-backend/models/`

---

### Step 3: Restart Backend & Verify

```bash
# 1. Stop any running backend (Ctrl+C in the terminal)

# 2. Run debug script to verify
cd python-backend
python debug_phase7.py

# Look for:
#   ✓ Model Files: Found: tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf (1200.5 MB)
#   ✓ LLM Service: LLM service READY
#     Model: tinyllama
#     Mode: LLM (full reasoning enabled)

# 3. Start backend
python main.py

# 4. Look for this in the logs:
#   [Phase 4] Initializing LLM service...
#   Loading Llama.cpp model from /path/to/models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf...
#   ✓ Llama.cpp model loaded successfully
#   ✓ LLM service READY (model loaded)
```

---

## Verify It's Working

After restart, test with the frontend:

1. **Upload a video**
2. **Send query:** "Summarize this video"
3. **Check response:** Should have insights, not just transcript snippets
4. **Generate PDF**
5. **Check PDF content:**
   - ✓ Section 1: Title + Metadata
   - ✓ Section 2: TL;DR (from LLM)
   - ✓ Section 3: Executive Summary (from LLM)
   - ✓ Section 4: Key Topics (from LLM)
   - ✓ Section 5: Scene Analysis
   - ✓ Section 6: Object Detection Results
   - ✓ Section 7: Graph Analysis (if applicable)
   - ✓ Section 8: Key Insights (from LLM)
   - ✓ Section 9: Conclusion (from LLM)

**If you see all 9 sections with LLM content → SUCCESS! ✓**

---

## Troubleshooting

### Issue: "Failed to load Llama.cpp model"

**Cause:** Model file is corrupted or wrong format

**Fix:**
1. Delete the broken file
2. Re-download from HuggingFace
3. Verify file size matches (should be ~1.2 GB for TinyLlama)

### Issue: "Out of memory" errors

**Cause:** System doesn't have enough RAM

**Fix:**
1. Close other applications
2. Try TinyLlama instead of Mistral (uses less RAM)
3. Increase virtual memory/swap space

### Issue: Very slow response times (30+ seconds per insight)

**Cause:** Running on CPU instead of GPU

**Fix:**
1. Install `llama-cpp-python` with GPU support
2. For NVIDIA: `pip install llama-cpp-python[cuda]`
3. For Apple Silicon: `pip install llama-cpp-python[metal]`

---

## Expected Performance

With TinyLlama on a modern CPU:

| Operation | Time |
|-----------|------|
| Transcription | 3-8 seconds |
| Vision Analysis | 5-10 seconds |
| Generate Summary | 5-10 seconds |
| Generate Insights | 10-15 seconds |
| PDF Generation | 2-3 seconds |
| **Total Pipeline** | **~30-50 seconds** |

---

## How to Verify Backend Logs

When you run `python main.py`, you should see:

**Good startup (LLM enabled):**
```
[Phase 4] Initializing LLM service...
✓ LLM service READY (model loaded)
  Model: tinyllama
  Mode: LLM (full reasoning enabled)
```

**Bad startup (LLM disabled):**
```
[Phase 4] Initializing LLM service...
ℹ LLM service in HEURISTIC MODE (model not available)
  To use LLM: download a GGUF model and place in ./models/
  Recommended: https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF
```

---

## Files to Check

After downloading a model, you should have:

```
intel-query-ai/
├── python-backend/
│   ├── models/                              # ← Create this if it doesn't exist
│   │   └── tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf  # ← ~1.2 GB file
│   ├── main.py
│   └── ...other files...
```

---

## Still Not Working?

1. **Run debug script:**
   ```bash
   cd python-backend
   python debug_phase7.py
   ```

2. **Check all 8 checks pass** (especially #3 "Model Files" and #6 "LLM Service")

3. **Look at backend startup logs** for any error messages

4. **Check file permissions:** Model file should be readable
   ```bash
   ls -lh python-backend/models/
   ```

5. **Verify model path is correct:** Should be something like:
   ```
   /path/to/intel-query-ai/python-backend/models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
   ```

---

## Next: Phase 7 Testing

Once LLM is working, follow the testing guide:
- [PHASE_7_TESTING_GUIDE.md](PHASE_7_TESTING_GUIDE.md)

All 7 test scenarios should now pass with LLM-generated insights in PDFs/PPTs!
