#!/bin/bash
# Setup and Run Wrapper for ARS on macOS

echo "Initializing Environment..."

# Check Python or setup venv
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Apply environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run Application
echo "Starting Scientist Agent..."
python main.py
