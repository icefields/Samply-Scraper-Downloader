#!/usr/bin/env python3
"""
Samply Track Tracker
Checks for version updates via browser automation and downloads changed files.
"""

import json
import subprocess
import re
from datetime import datetime
from pathlib import Path

STATE_FILE = Path(__file__).parent / "samply_tracker_state.json"
DOWNLOADS_DIR = Path(__file__).parent / "samply_downloads"


def load_state():
    with open(STATE_FILE) as f:
        return json.load(f)


def save_state(state):
    state["last_check"] = datetime.now().isoformat()
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def get_cdn_url(state, file_id):
    """Build CDN URL for a file."""
    return f"{state['cdn_base']}/{file_id}/output/aac256k@output.mp4"


def download_track(state, track):
    """Download a single track from CDN."""
    url = get_cdn_url(state, track["file_id"])
    mp4_path = DOWNLOADS_DIR / f"{track['file_id']}.mp4"
    mp3_path = DOWNLOADS_DIR / track["name"]
    
    # Download MP4
    print(f"Downloading {track['name']}...")
    subprocess.run([
        "curl", "-L", "-o", str(mp4_path), url
    ], check=True, capture_output=True)
    
    # Convert to MP3
    print(f"Converting to MP3...")
    subprocess.run([
        "ffmpeg", "-y", "-i", str(mp4_path),
        "-c:a", "libmp3lame", "-q:a", "2",
        str(mp3_path)
    ], check=True, capture_output=True)
    
    # Cleanup MP4
    mp4_path.unlink()
    print(f"✓ {track['name']} downloaded")
    
    return True


def main():
    state = load_state()
    print(f"Samply Tracker - {state['project_name']}")
    print(f"Artist: {state['artist']}")
    print(f"URL: {state['url']}")
    print()
    print("Tracks:")
    for track in state["tracks"]:
        status = "✓ downloaded" if track.get("downloaded") else "○ pending"
        print(f"  [{status}] {track['name']} (v{track['version']}) - {track['duration']}")
    print()
    print(f"Last check: {state.get('last_check', 'never')}")
    print(f"Downloads: {DOWNLOADS_DIR}")


if __name__ == "__main__":
    main()