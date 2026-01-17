#!/usr/bin/env bash
# Exit on error
set -o errexit

# 1. Install Python Dependencies
pip install -r requirements.txt

# 2. Install FFmpeg (Static Build)
mkdir -p ffmpeg_bin
echo "Downloading FFmpeg..."
wget -q https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
tar -xf ffmpeg-release-amd64-static.tar.xz -C ffmpeg_bin --strip-components 1
rm ffmpeg-release-amd64-static.tar.xz
echo "FFmpeg installed successfully."
