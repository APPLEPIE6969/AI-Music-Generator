#!/usr/bin/env bash
# Exit on error
set -o errexit

# 1. Install Python Dependencies
pip install -r requirements.txt

# 2. Install FFmpeg (Static Build)
# Create a folder for ffmpeg
mkdir -p ffmpeg_bin

# Download the static build of FFmpeg
echo "Downloading FFmpeg..."
wget -q https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz

# Extract it
tar -xf ffmpeg-release-amd64-static.tar.xz -C ffmpeg_bin --strip-components 1

# Clean up tar file
rm ffmpeg-release-amd64-static.tar.xz

echo "FFmpeg installed successfully."
