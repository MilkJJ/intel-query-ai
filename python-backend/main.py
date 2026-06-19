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
from services.grpc_service_manager import get_grpc_service_manager
from services.llama_service import get_llama_service

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Intel Query AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
agent_router = build_agent_router()

# Initialize gRPC services (Phase 2)
grpc_manager = get_grpc_service_manager(enable_grpc=True)

# Initialize LLM service (Phase 4 - now fully integrated)
llama_service = get_llama_service(model_path=None, enable_llm=True)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("=" * 80)
    logger.info("INTEL QUERY AI - BACKEND STARTUP")
    logger.info("=" * 80)
    logger.info("")
    
    # Start gRPC services (Phase 2)
    logger.info("[Phase 2] Starting gRPC services...")
    try:
        if grpc_manager.start_services():
            status = grpc_manager.status()
            logger.info("✓ gRPC services initialized successfully")
            for svc, info in status.items():
                logger.info("  - %s: %s", svc, info)
        else:
            logger.warning("⚠ Some gRPC services failed to start (running in fallback mode)")
    except Exception as e:
        logger.error("✗ gRPC startup error: %s", e)
    
    logger.info("")
    
    # Initialize LLM service (Phase 4 - fully integrated)
    logger.info("[Phase 4] Initializing LLM service...")
    try:
        llm_status = llama_service.health_check()
        if llm_status["ready"]:
            logger.info("✓ LLM service READY (model loaded)")
            logger.info("  Model: %s", llm_status.get("model_name", "unknown"))
            logger.info("  Mode: %s (full reasoning enabled)", llm_status.get("mode"))
        else:
            logger.info("ℹ LLM service in HEURISTIC MODE (model not available)")
            if llm_status["enabled"]:
                logger.info("  To use LLM: download a GGUF model and place in ./models/")
                logger.info("  Recommended: %s", llama_service.DEFAULT_MODELS.get("tinyllama"))
            else:
                logger.info("  LLM is disabled")
    except Exception as e:
        logger.error("✗ LLM service error: %s", e)
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("Backend ready for requests!")
    logger.info("=" * 80)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Intel Query AI backend...")
    grpc_manager.stop_services()




@app.get("/")
async def health():
    """Health check endpoint with service status."""
    grpc_status = grpc_manager.status() if grpc_manager else {}
    llm_status = llama_service.health_check() if llama_service else {}
    
    return {
        "status": "ok",
        "version": "1.0.0",
        "grpc_services": grpc_status,
        "llm_service": llm_status,
    }


@app.get("/status")
async def status():
    """Detailed system status endpoint."""
    llm_info = llama_service.health_check() if llama_service else {}
    llm_model = llm_info.get("model_name", "tinyllama")
    llm_mode = llm_info.get("mode", "unknown")
    
    return {
        "backend": "online",
        "grpc_enabled": grpc_manager.enable_grpc if grpc_manager else False,
        "grpc_services": grpc_manager.status() if grpc_manager else {},
        "llm_service": llm_info,
        "models": {
            "transcription": "faster-whisper:base (int8)",
            "vision": "facebook/detr-resnet-50, Salesforce/blip-image-captioning-base",
            "generation": f"{llm_model} ({llm_mode} mode, Phase 4)",
        },
    }


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
