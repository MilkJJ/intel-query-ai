"""
GRPCServiceManager — launches and manages gRPC service processes.

Responsibilities:
  - Spawn gRPC servers for transcription, vision, generation in background threads
  - Manage service lifecycle (start, stop, health check)
  - Provide configuration for gRPC client initialization
  - Handle graceful shutdown
"""

import logging
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)


class GRPCServiceManager:
    """Manages gRPC service processes."""

    def __init__(self, enable_grpc: bool = True):
        """
        Initialize service manager.
        
        Args:
            enable_grpc: Whether to spawn gRPC servers (default: True)
        """
        self.enable_grpc = enable_grpc
        self.services = {}
        self.threads = {}
        self.lock = threading.Lock()

    def start_services(self) -> bool:
        """
        Start all gRPC services in background threads.
        
        Returns:
            True if all services started successfully, False otherwise
        """
        if not self.enable_grpc:
            logger.info("gRPC services disabled (enable_grpc=False)")
            return True

        logger.info("Starting gRPC services...")

        try:
            # Start TranscriptionService
            self._start_service("transcription", "services.grpc_servers.transcription_mcp", 50051)

            # Start VisionService
            self._start_service("vision", "services.grpc_servers.vision_mcp", 50052)

            # Start GenerationService
            self._start_service("generation", "services.grpc_servers.generation_mcp", 50053)

            # Give services time to start
            time.sleep(2)

            # Verify services are up
            if self._verify_services():
                logger.info("✓ All gRPC services started successfully")
                return True
            else:
                logger.warning("Some gRPC services failed to start or respond")
                return False

        except Exception as e:
            logger.error("Failed to start gRPC services: %s", e)
            return False

    def _start_service(self, service_name: str, module_path: str, port: int):
        """
        Start a single gRPC service in a background thread.
        
        Args:
            service_name: Name of service (e.g., "transcription")
            module_path: Python module path (e.g., "services.grpc_servers.transcription_mcp")
            port: gRPC port number
        """
        def run_service():
            try:
                # Dynamically import and run service
                module = __import__(module_path, fromlist=["serve"])
                logger.info("Starting %s service on port %d", service_name, port)
                module.serve(port)
            except Exception as e:
                logger.error("Service %s failed: %s", service_name, e)

        thread = threading.Thread(target=run_service, daemon=True, name=f"grpc-{service_name}")
        thread.start()
        self.threads[service_name] = thread
        self.services[service_name] = {
            "port": port,
            "thread": thread,
            "status": "starting",
        }

        logger.info("Started %s service thread", service_name)

    def _verify_services(self) -> bool:
        """
        Verify all gRPC services are responding to pings.
        
        Returns:
            True if all services respond, False otherwise
        """
        from clients.transcription_client import TranscriptionClient
        from clients.vision_client import VisionClient
        from clients.generation_client import GenerationClient

        clients = [
            ("transcription", TranscriptionClient()),
            ("vision", VisionClient()),
            ("generation", GenerationClient()),
        ]

        all_healthy = True
        for service_name, client in clients:
            if client.connect():
                self.services[service_name]["status"] = "healthy"
                client.close()
            else:
                self.services[service_name]["status"] = "unhealthy"
                all_healthy = False

        return all_healthy

    def get_grpc_config(self) -> dict:
        """
        Get gRPC configuration for clients.
        
        Returns:
            Dict with host, port for each service
        """
        return {
            "enabled": self.enable_grpc,
            "transcription": {
                "host": "localhost",
                "port": 50051,
            },
            "vision": {
                "host": "localhost",
                "port": 50052,
            },
            "generation": {
                "host": "localhost",
                "port": 50053,
            },
        }

    def stop_services(self):
        """Stop all gRPC services."""
        logger.info("Stopping gRPC services...")
        # Services run as daemon threads, so they'll stop when main thread exits
        self.services.clear()
        self.threads.clear()
        logger.info("✓ gRPC services stopped")

    def status(self) -> dict:
        """Get status of all gRPC services."""
        return {
            service_name: service.get("status", "unknown")
            for service_name, service in self.services.items()
        }


# Global service manager instance
_service_manager: Optional[GRPCServiceManager] = None


def get_grpc_service_manager(enable_grpc: bool = True) -> GRPCServiceManager:
    """
    Get or create global gRPC service manager.
    
    Args:
        enable_grpc: Whether to enable gRPC services
        
    Returns:
        GRPCServiceManager instance
    """
    global _service_manager
    if _service_manager is None:
        _service_manager = GRPCServiceManager(enable_grpc=enable_grpc)
    return _service_manager
