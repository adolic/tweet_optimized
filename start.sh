#!/bin/bash

# Kill background processes when script is terminated
trap 'kill $(jobs -p)' EXIT

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Store the root directory
ROOT_DIR=$(pwd)

echo -e "${BLUE}Starting LLM-DOCS services...${NC}"

# Start backend
echo -e "${GREEN}Starting backend service...${NC}"
cd "$ROOT_DIR/backend" && uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# Check if backend started successfully
if ! ps -p $BACKEND_PID > /dev/null; then
    echo -e "${RED}Failed to start backend service${NC}"
    exit 1
fi

# Wait a bit for backend to initialize
sleep 2

# Start frontend
echo -e "${GREEN}Starting frontend service...${NC}"
cd "$ROOT_DIR/frontend" && npm run dev &
FRONTEND_PID=$!

# Check if frontend started successfully
if ! ps -p $FRONTEND_PID > /dev/null; then
    echo -e "${RED}Failed to start frontend service${NC}"
    exit 1
fi

echo -e "${GREEN}All services started successfully!${NC}"
echo -e "${BLUE}Backend running at:${NC} http://localhost:8000"
echo -e "${BLUE}Frontend running at:${NC} http://localhost:5173"

# Keep script running
wait 