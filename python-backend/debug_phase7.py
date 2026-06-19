#!/usr/bin/env python3
"""
Debug script to verify Phase 7 implementation and LLM status.
Run this from the python-backend directory.
"""

import os
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

def check_python_version():
    """Verify Python version."""
    logger.info("=" * 80)
    logger.info("PHASE 7: SYSTEM VERIFICATION")
    logger.info("=" * 80)
    
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        logger.info("✓ Python 3.10+ detected: %s.%s", version.major, version.minor)
        return True
    else:
        logger.error("✗ Python 3.10+ required, found: %s.%s", version.major, version.minor)
        return False

def check_dependencies():
    """Check if required packages are installed."""
    required_packages = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("pydantic", "Pydantic"),
        ("faster_whisper", "Faster-Whisper"),
        ("PIL", "Pillow (Image processing)"),
        ("grpc", "gRPC"),
        ("reportlab", "ReportLab (PDF generation)"),
        ("pptx", "python-pptx (PowerPoint generation)"),
    ]
    
    logger.info("\n[1] Checking dependencies...")
    all_good = True
    for pkg_name, display_name in required_packages:
        try:
            __import__(pkg_name)
            logger.info("  ✓ %s installed", display_name)
        except ImportError:
            logger.error("  ✗ %s NOT installed", display_name)
            all_good = False
    
    return all_good

def check_llm_module():
    """Check if llama-cpp-python is available."""
    logger.info("\n[2] Checking LLM module...")
    try:
        import llama_cpp
        logger.info("  ✓ llama-cpp-python installed")
        return True
    except ImportError:
        logger.warning("  ⚠ llama-cpp-python NOT installed")
        logger.warning("    Install with: pip install llama-cpp-python")
        return False

def check_model_files():
    """Check if GGUF model files exist."""
    logger.info("\n[3] Checking for GGUF model files...")
    
    search_dirs = [
        Path("./models"),
        Path("../models"),
        Path.home() / ".cache" / "llama.cpp",
        Path.home() / ".cache" / "huggingface" / "hub",
    ]
    
    found_models = []
    for search_dir in search_dirs:
        if search_dir.exists():
            for root, dirs, files in os.walk(search_dir):
                for file in files:
                    if file.endswith(".gguf"):
                        model_path = Path(root) / file
                        found_models.append(model_path)
                        logger.info(
                                "  ✓ Found: %s (%.1f MB)",
                                file,
                                model_path.stat().st_size / (1024 * 1024)
                            )
    
    if not found_models:
        logger.error("  ✗ No GGUF model files found!")
        logger.error("    Download from: https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF")
        logger.error("    Place in: ./models/ directory")
        return False
    
    return True

def check_proto_files():
    """Check if gRPC proto files are compiled."""
    logger.info("\n[4] Checking gRPC proto compilation...")

    # Proto stubs are generated under ./proto in this project.
    # Keep compatibility with older layouts that generated to services/grpc_servers.
    file_alternatives = [
        (
            "transcription_pb2.py",
            [
                "proto/transcription_pb2.py",
                "services/grpc_servers/transcription_pb2.py",
            ],
        ),
        (
            "transcription_pb2_grpc.py",
            [
                "proto/transcription_pb2_grpc.py",
                "services/grpc_servers/transcription_pb2_grpc.py",
            ],
        ),
        (
            "vision_pb2.py",
            [
                "proto/vision_pb2.py",
                "services/grpc_servers/vision_pb2.py",
            ],
        ),
        (
            "vision_pb2_grpc.py",
            [
                "proto/vision_pb2_grpc.py",
                "services/grpc_servers/vision_pb2_grpc.py",
            ],
        ),
        (
            "generation_pb2.py",
            [
                "proto/generation_pb2.py",
                "services/grpc_servers/generation_pb2.py",
            ],
        ),
        (
            "generation_pb2_grpc.py",
            [
                "proto/generation_pb2_grpc.py",
                "services/grpc_servers/generation_pb2_grpc.py",
            ],
        ),
    ]

    all_good = True
    for logical_name, candidates in file_alternatives:
        found = next((path for path in candidates if Path(path).exists()), None)
        if found:
            logger.info("  ✓ %s (%s)", logical_name, found)
        else:
            logger.error("  ✗ %s MISSING", logical_name)
            all_good = False

    if not all_good:
        logger.info("    Run: python -m grpc_tools.protoc -I proto --python_out=proto --grpc_python_out=proto proto/*.proto")

    return all_good

def check_python_syntax():
    """Check Python files for syntax errors."""
    logger.info("\n[5] Checking Python syntax...")
    
    python_files = [
        "main.py",
        "agents/router_agent.py",
        "agents/generation_agent.py",
        "agents/report_agent.py",
        "services/llama_service.py",
        "services/multimodal_pipeline.py",
    ]
    
    import py_compile
    all_good = True
    for file_path in python_files:
        try:
            py_compile.compile(file_path, doraise=True)
            logger.info("  ✓ %s", file_path)
        except py_compile.PyCompileError as e:
            logger.error("  ✗ %s - %s", file_path, str(e)[:100])
            all_good = False
    
    return all_good

def check_llm_service():
    """Try to initialize LLM service and check its status."""
    logger.info("\n[6] Checking LLM service initialization...")
    
    try:
        from services.llama_service import get_llama_service
        
        llm_service = get_llama_service(enable_llm=True)
        health = llm_service.health_check()
        
        if health.get("ready"):
            logger.info("  ✓ LLM service READY")
            logger.info("    Model: %s", health.get("model_name"))
            logger.info("    Mode: LLM (full reasoning)")
            return True
        else:
            logger.warning("  ⚠ LLM service in HEURISTIC MODE")
            if health.get("enabled"):
                logger.warning("    Model not found, but service enabled")
            logger.warning("    To enable LLM: download a .gguf model file")
            return False
    except Exception as e:
        logger.error("  ✗ Error checking LLM service: %s", str(e)[:100])
        return False

def check_agents():
    """Check if all agents can be initialized."""
    logger.info("\n[7] Checking agent registration...")
    
    try:
        from agents.registry import build_default_registry
        
        registry = build_default_registry()
        agents = registry.all()

        # Current architecture registers 5 agents.
        # MultimodalPipeline is a service dependency, not a BaseAgent entry.
        if len(agents) >= 5:
            logger.info("  ✓ All agents registered (%d total)", len(agents))
            for agent in agents:
                logger.info("    - %s", agent.name)
            return True
        else:
            logger.error("  ✗ Expected 5+ agents, found %d", len(agents))
            return False
    except Exception as e:
        logger.error("  ✗ Error registering agents: %s", str(e)[:100])
        return False

def main():
    """Run all checks."""
    results = []
    
    results.append(("Python Version", check_python_version()))
    results.append(("Dependencies", check_dependencies()))
    results.append(("LLM Module", check_llm_module()))
    results.append(("Model Files", check_model_files()))
    results.append(("Proto Files", check_proto_files()))
    results.append(("Python Syntax", check_python_syntax()))
    results.append(("LLM Service", check_llm_service()))
    results.append(("Agent Registry", check_agents()))
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info("%s: %s", status, name)
    
    logger.info("\nResult: %d/%d checks passed", passed, total)
    
    if passed == total:
        logger.info("\n🎉 All checks passed! System is ready.")
        if check_model_files():
            logger.info("✓ LLM insights will be enabled in reports")
        else:
            logger.info("⚠ Download a model to enable LLM insights (see guide above)")
    else:
        logger.error("\n❌ Some checks failed. See errors above.")
        logger.error("   Critical issues:")
        if not check_python_syntax():
            logger.error("   - Fix Python syntax errors")
        if not check_proto_files():
            logger.error("   - Regenerate gRPC proto files")
        if not check_model_files():
            logger.error("   - Download a GGUF model for LLM support")

if __name__ == "__main__":
    main()
