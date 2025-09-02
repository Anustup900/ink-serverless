#!/bin/bash
set -e

# Start ComfyUI API server in the background
echo "Starting ComfyUI API server..."
python main.py --listen 0.0.0.0 --port 8188 --output-directory /workspace/ComfyUI/output &

# Small delay to ensure server boots
sleep 5

# Start RunPod handler
echo "Starting RunPod handler..."
python handler.py
