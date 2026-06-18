import logging
import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, Response, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from agents.context import AgentContext
from agents.router import build_agent_router
from schemas import ExportRequest, QueryResponse
from services.export_service import generate_export_file
from services.media_service import SUPPORTED_VIDEO_FORMATS

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent_router = build_agent_router()




@app.get("/")
async def health():
    return {"status": "ok"}


@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)

@app.post("/upload")
async def upload(file: UploadFile):
    return {"filename": file.filename}


@app.post("/query", response_model=QueryResponse)
async def query_video(file: UploadFile = File(...), query: str = Form(...)):
    """
    Upload a video and get its transcription.
    Returns transcribed text that can be queried.
    """
    
    logger.info(f"Processing request: file={file.filename}, query={query}")
    
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in SUPPORTED_VIDEO_FORMATS:
        logger.error(f"Unsupported format: {file_ext}")
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported format. Supported: {', '.join(SUPPORTED_VIDEO_FORMATS)}"
        )
    
    temp_dir = tempfile.mkdtemp()
    video_path = None
    
    try:
        # Save uploaded video
        video_path = os.path.join(temp_dir, file.filename)
        logger.info(f"Saving video to {video_path}...")
        
        with open(video_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"✓ Video saved. Size: {os.path.getsize(video_path)} bytes")

        agent_result = agent_router.handle(AgentContext(video_path=video_path, query=query))
        
        logger.info(f"✓ Request completed successfully")
        
        return QueryResponse(
            success=True,
            filename=file.filename,
            query=query,
            agent=agent_result.agent,
            action=agent_result.action,
            result=agent_result.response,
            confidence=agent_result.confidence,
            transcription=agent_result.transcription,
            transcript_summary=agent_result.metadata.get("transcript_summary", ""),
            detected_objects=agent_result.metadata.get("detected_objects", []),
            frame_text=agent_result.metadata.get("frame_text", []),
            language=agent_result.language,
            duration=agent_result.duration,
            objects=agent_result.objects,
            note=agent_result.note,
            metadata=agent_result.metadata,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    
    finally:
        # Cleanup temporary files
        try:
            if video_path and os.path.exists(video_path):
                os.remove(video_path)
                logger.info("✓ Cleaned up video file")
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
                logger.info("✓ Cleaned up temp directory")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")


@app.post("/export")
async def export_output(payload: ExportRequest):
    try:
        file_buffer, media_type, download_name = generate_export_file(payload)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return StreamingResponse(
        file_buffer,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'},
    )
