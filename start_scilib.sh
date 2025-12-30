#!/usr/bin/env bash
#
# SciLib AI Startup Script
#
# This script starts all necessary services for the SciLib AI-powered 
# scientific literature manager:
#
# 1. Redis server (for Celery task queue)
# 2. Celery worker (for background AI tasks)  
# 3. FastAPI server (main application)
#
# Usage:
#     ./start_scilib.sh [--dev]
#     
# Options:
#     --dev    Start in development mode with auto-reload
#

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m' 
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Starting SciLib AI-powered Literature Manager${NC}"
echo "=================================================="

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo -e "${BLUE}Activating virtual environment...${NC}"
    source .venv/bin/activate
    echo -e "${GREEN}✓${NC} Virtual environment activated"
fi

# Check if Redis is running
check_redis() {
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Redis is running"
        return 0
    else
        echo -e "${YELLOW}⚠${NC} Redis is not running"
        return 1
    fi
}

# Start Redis if not running
start_redis() {
    echo -e "${BLUE}Starting Redis server...${NC}"
    if command -v redis-server > /dev/null 2>&1; then
        redis-server --daemonize yes --port 6379
        sleep 2
        if check_redis; then
            echo -e "${GREEN}✓${NC} Redis started successfully"
        else
            echo -e "${RED}✗${NC} Failed to start Redis"
            exit 1
        fi
    else
        echo -e "${RED}✗${NC} Redis not found. Please install Redis:"
        echo "  macOS: brew install redis"
        echo "  Ubuntu: sudo apt install redis-server" 
        exit 1
    fi
}

# Check Python environment
check_python_env() {
    if python -c "import fastapi, langchain, celery" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Python dependencies available"
    else
        echo -e "${YELLOW}⚠${NC} Missing dependencies. Installing..."
        pip install -r requirements.txt
    fi
}

# Start Celery worker in background
start_celery() {
    echo -e "${BLUE}Starting Celery worker...${NC}"
    
    # Stop any existing Celery workers first
    if pgrep -f "celery.*worker" > /dev/null; then
        echo -e "${YELLOW}Stopping existing Celery workers...${NC}"
        pkill -f "celery.*worker"
        sleep 2
        echo -e "${GREEN}✓${NC} Stopped old workers"
    fi
    
    export PYTHONPATH="${PYTHONPATH}:$(pwd)"
    
    # Check if DEBUG mode is enabled
    if grep -q "^DEBUG=True" .env 2>/dev/null || grep -q "^DEBUG=true" .env 2>/dev/null; then
        echo -e "${YELLOW}DEBUG mode detected - showing Celery output in terminal${NC}"
        # Don't redirect to file - show colored output in terminal
        python app/celery_worker.py &
    else
        # Production mode - redirect to log file
        python app/celery_worker.py > logs/celery.log 2>&1 &
    fi
    
    CELERY_PID=$!
    echo $CELERY_PID > celery.pid
    sleep 3
    
    if ps -p $CELERY_PID > /dev/null; then
        echo -e "${GREEN}✓${NC} Celery worker started (PID: $CELERY_PID)"
        if grep -q "^DEBUG=True" .env 2>/dev/null || grep -q "^DEBUG=true" .env 2>/dev/null; then
            echo -e "${YELLOW}  Debug output will appear below when tasks run${NC}"
        else
            echo -e "${BLUE}  Logs available at: logs/celery.log${NC}"
        fi
    else
        echo -e "${RED}✗${NC} Failed to start Celery worker"
        [ -f logs/celery.log ] && cat logs/celery.log
        exit 1
    fi
}

# Start FastAPI server
start_fastapi() {
    local dev_mode=$1
    echo -e "${BLUE}Starting FastAPI server...${NC}"
    
    if [ "$dev_mode" = "true" ]; then
        echo -e "${YELLOW}Development mode enabled${NC}"
        uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    else
        uvicorn app.main:app --host 0.0.0.0 --port 8000
    fi
}

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    
    # Stop Celery worker
    if [ -f celery.pid ]; then
        CELERY_PID=$(cat celery.pid)
        if ps -p $CELERY_PID > /dev/null; then
            echo "Stopping Celery worker (PID: $CELERY_PID)"
            kill $CELERY_PID
        fi
        rm -f celery.pid
    fi
    
    echo -e "${GREEN}✓${NC} Cleanup complete"
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Main execution
main() {
    local dev_mode=false
    
    # Parse arguments
    if [ "$1" = "--dev" ]; then
        dev_mode=true
    fi
    
    # Check and start Redis
    if ! check_redis; then
        start_redis
    fi
    
    # Check Python environment
    check_python_env
    
    # Start services
    start_celery
    
    echo -e "\n${GREEN}🚀 All services started successfully!${NC}"
    echo "=================================="
    echo -e "📖 Web Interface: ${BLUE}http://localhost:8000${NC}"
    echo -e "📊 API Docs: ${BLUE}http://localhost:8000/docs${NC}"
    echo -e "🔧 Redis: ${BLUE}localhost:6379${NC}"
    echo ""
    echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
    echo ""
    
    # Start FastAPI (this will block)
    start_fastapi $dev_mode
}

# Run main function with all arguments
main "$@"