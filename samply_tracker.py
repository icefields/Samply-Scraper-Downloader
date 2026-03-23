#!/usr/bin/env python3
"""
Samply Track Tracker
Displays project info and track status.
Uses .env.samply or .env for configuration.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment from .env first (user config), fallback to .env.samply (defaults)
env_path = Path(__file__).parent
load_dotenv(env_path / ".env", override=True)
load_dotenv(env_path / ".env.samply")

# Config from environment
STATE_FILE = Path(os.path.expanduser(os.getenv("SAMPLY_STATE_FILE", str(Path(__file__).parent / "samply_tracker_state.json"))))
DOWNLOADS_DIR = Path(os.path.expanduser(os.getenv("SAMPLY_DOWNLOADS_DIR", str(Path(__file__).parent / "samply_downloads"))))


def load_state():
    with open(STATE_FILE) as f:
        return json.load(f)


def save_state(state):
    state["last_check"] = datetime.now().isoformat()
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def main():
    state = load_state()
    
    print(f"Samply Tracker - {state.get('project_name', os.getenv('SAMPLY_PROJECT_NAME', 'Unknown'))}")
    print(f"Artist: {state.get('artist', os.getenv('SAMPLY_ARTIST', 'Unknown'))}")
    print(f"URL: {state.get('url', os.getenv('SAMPLY_URL', 'N/A'))}")
    print()
    print("Tracks:")
    for track in state.get("tracks", []):
        status = "✓ downloaded" if track.get("downloaded") else "○ pending"
        print(f"  [{status}] {track['name']} (v{track['version']}) - {track.get('duration', '?')}")
    print()
    print(f"Last check: {state.get('last_check', 'never')}")
    print(f"Downloads: {DOWNLOADS_DIR}")


if __name__ == "__main__":
    main()