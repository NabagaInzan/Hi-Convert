#!/usr/bin/env bash
# exit on error
set -o errexit

# Install Poppler
chmod +x install_poppler.sh
./install_poppler.sh

# Install Python dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Run migrations
python manage.py migrate
