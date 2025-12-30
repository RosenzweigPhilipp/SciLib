#!/usr/bin/env python3
"""
Celery worker startup script for SciLib AI tasks.

Usage:
    python celery_worker.py

This starts a Celery worker that processes background AI extraction tasks.
"""
import os
import sys
import logging
from pathlib import Path

# Add the app directory to the path
project_root = Path(__file__).parent.parent
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

# Load environment variables from project .env so workers have keys
try:
    from dotenv import load_dotenv
    load_dotenv(project_root / ".env")
except Exception:
    # dotenv is optional in some setups; proceed if not available
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

def main():
    """Start the Celery worker."""
    try:
        # Import Celery app
        from app.ai.tasks import celery_app
        
        if not celery_app:
            logger.error("Celery not available. Please install with: pip install celery redis")
            return 1
        
        logger.info("Starting SciLib AI Celery worker...")
        
        # Start worker (listen to both 'celery' and 'default' queues so existing tasks are picked up)
        celery_app.worker_main([
            "worker",
            "--loglevel=debug",
            "--concurrency=2",  # Limit concurrent tasks
            "--prefetch-multiplier=1",
            "--queues=celery,default",
            "--hostname=scilib-ai-worker@%h"
        ])
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        return 0
    except Exception as e:
        logger.error(f"Failed to start Celery worker: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())