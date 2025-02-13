#!/usr/bin/env bash
# exit on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Create required directories
mkdir -p uploads
mkdir -p logs
