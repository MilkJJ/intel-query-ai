# Video Transcription Backend Setup Guide

## Prerequisites

### 1. **Install FFmpeg** (Required for audio extraction)

#### Windows
```powershell
# Using Chocolatey
choco install ffmpeg

# OR Using Scoop
scoop install ffmpeg

# OR Download from https://ffmpeg.org/download.html
```

#### macOS
```bash
brew install ffmpeg
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

#### Linux (Fedora)
```bash
sudo dnf install ffmpeg
```

**Verify installation:**
```bash
ffmpeg -version
```

### 2. **Install Python Dependencies**

```bash
cd python-backend
pip install -r requirements.txt
```

### 3. **Check All Dependencies**

```bash
python check_dependencies.py
```

Expected output:
```
✓ FFmpeg installed: ffmpeg version X.X.X
✓ fastapi installed
✓ uvicorn installed
✓ faster_whisper installed
```

## Running the Backend

### Development Mode (with auto-reload)
```bash
cd python-backend
uvicorn main:app --reload --port 8000
```

### Production Mode
```bash
cd python-backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
✓ Whisper model loaded successfully
```

## API Endpoints

### GET `/` - Health Check
```bash
curl http://localhost:8000/
# Response: {"status": "ok"}
```

### POST `/query` - Upload and Transcribe
```bash
curl -X POST http://localhost:8000/query \
  -F "file=@video.mp4" \
  -F "query=Transcribe this video"
```

Response:
```json
{
  "success": true,
  "filename": "video.mp4",
  "query": "Transcribe this video",
  "transcription": "Full transcribed text...",
  "language": "en",
  "duration": 45.2
}
```

## Troubleshooting

### Error: "FFmpeg not found"
- Make sure FFmpeg is installed and added to your system PATH
- Restart your terminal/IDE after installing FFmpeg
- Test with: `ffmpeg -version`

### Error: "Whisper model not initialized"
- The model (~140MB) needs to download on first run
- Ensure you have internet connection and disk space
- Check the terminal for download progress

### Error: 500 Internal Server Error
1. Check the backend terminal for detailed error messages
2. Run `python check_dependencies.py` to verify setup
3. Ensure the uploaded video file is not corrupted
4. Check file permissions on the temp directory

### Slow Transcription
- The CPU version (int8) is used for compatibility
- First run downloads the model (~140MB)
- Transcription speed depends on video length and CPU
- A 1-hour video typically takes 2-3 minutes on modern CPUs

## Performance Tips

- Use smaller video files for faster processing
- Ensure sufficient RAM (4GB minimum recommended)
- Close unnecessary background applications
- Consider using GPU version (requires CUDA): `WhisperModel("base", device="cuda")`

## Model Information

- **Model**: `base` (smaller, faster)
- **Size**: ~140MB
- **Languages**: Supports 99+ languages
- **Accuracy**: Good balance between speed and accuracy
- **Alternative**: Use "tiny" for faster but less accurate results

## File Cleanup

The backend automatically removes temporary files after processing. If you need to manually clean up:

```bash
# Windows
rmdir /s %TEMP%\tmp*

# Linux/macOS
rm -rf /tmp/tmp*
```
