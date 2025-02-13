#!/bin/bash

# Create directory for Poppler
mkdir -p /opt/render/project/poppler

# Download and extract Poppler
wget -q -O poppler.tar.gz "https://github.com/oschwartz10612/poppler-windows/releases/download/v24.02.0-0/Release-24.02.0-0.zip"
unzip -q poppler.tar.gz -d /opt/render/project/poppler
rm poppler.tar.gz

# Update environment variable
export POPPLER_PATH=/opt/render/project/poppler/Library/bin
