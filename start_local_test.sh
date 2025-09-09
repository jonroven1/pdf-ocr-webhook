#!/bin/bash

# Start Local PDF OCR Webhook for Testing
# This script sets up the webhook locally and provides ngrok for external access

echo "🚀 Starting PDF OCR Webhook for Local Testing"
echo "=============================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run the setup first."
    echo "Run: python3 -m venv venv && source venv/bin/activate && pip install -r webhook_requirements.txt"
    exit 1
fi

# Set environment variables
export PDF_SERVICES_CLIENT_ID=bc4b6b89bfc1457b89ed7a2ef920ccbe
export PDF_SERVICES_CLIENT_SECRET=p8e-XfFf7D42xo0wSNaDAWHgEIapRRd_N1ed

echo "✅ Environment variables set"

# Activate virtual environment and start webhook
echo "🔧 Starting webhook server..."
source venv/bin/activate

# Start webhook in background
python webhook_ocr.py &
WEBHOOK_PID=$!

# Wait a moment for webhook to start
sleep 3

# Check if webhook is running
if curl -s http://localhost:5001/health > /dev/null; then
    echo "✅ Webhook is running on http://localhost:5001"
    
    # Check if ngrok is installed
    if command -v ngrok &> /dev/null; then
        echo "🌐 Starting ngrok tunnel..."
        echo "Your webhook will be available at the ngrok URL shown below"
        echo "Use this URL in your Zapier webhook configuration"
        echo ""
        echo "Press Ctrl+C to stop both webhook and ngrok"
        echo "=============================================="
        
        # Start ngrok
        ngrok http 5001
    else
        echo "⚠️  ngrok not found. Install it with: brew install ngrok"
        echo "Then run: ngrok http 5001"
        echo ""
        echo "Your webhook is running locally at: http://localhost:5001"
        echo "Press Ctrl+C to stop the webhook"
        wait $WEBHOOK_PID
    fi
else
    echo "❌ Failed to start webhook. Check the logs above."
    kill $WEBHOOK_PID 2>/dev/null
    exit 1
fi
