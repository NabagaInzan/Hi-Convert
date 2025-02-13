#!/usr/bin/env bash
# exit on error
set -o errexit

# Install system dependencies
apt-get update
apt-get install -y poppler-utils python3-opencv

# Upgrade pip
python -m pip install --upgrade pip

# Install Python dependencies
pip install --no-cache-dir -r requirements.txt

# Create required directories
mkdir -p uploads
mkdir -p logs
