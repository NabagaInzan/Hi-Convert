#!/usr/bin/env bash
# exit on error
set -o errexit

# Install Poppler
chmod +x install_poppler.sh
./install_poppler.sh

# Install Python dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p staticfiles media uploads outputs

# Collect static files
python manage.py collectstatic --no-input

# Run migrations
python manage.py migrate
