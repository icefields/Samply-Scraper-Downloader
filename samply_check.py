#!/usr/bin/env python3
"""
Samply Update Checker
Run by cron job to check for version updates.
Uses OpenClaw browser automation to get current versions.
"""

import json
import subprocess
import sys
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
    return f"{state['cdn_base']}/{file_id}/output/aac256k@output.mp4"


def download_track(state, track, prefer_flac=True):
    """Download and convert a track to Opus 192kbps.
    
    If prefer_flac=True and FLAC is available, downloads FLAC version.
    Otherwise downloads AAC 256kbps version.
    Converts to Opus with user's preferred settings.
    """
    base_url = f"{state['cdn_base']}/{track['file_id']}/output"
    
    # Try FLAC first if preferred
    source_path = None
    if prefer_flac:
        flac_url = f"{base_url}/flac@output.mp4"
        flac_path = DOWNLOADS_DIR / f"{track['file_id']}_flac.mp4"
        result = subprocess.run(
            ["curl", "-L", "-f", "-o", str(flac_path), flac_url],
            capture_output=True
        )
        if result.returncode == 0:
            source_path = flac_path
            print(f"  Downloaded FLAC source")
    
    # Fall back to AAC if no FLAC
    if not source_path:
        aac_url = f"{base_url}/aac256k@output.mp4"
        aac_path = DOWNLOADS_DIR / f"{track['file_id']}_aac.mp4"
        subprocess.run(["curl", "-L", "-o", str(aac_path), aac_url], check=True, capture_output=True)
        source_path = aac_path
        print(f"  Downloaded AAC source")
    
    # Convert to Opus 192kbps with user's preferred settings
    base_name = Path(track["name"]).stem
    opus_path = DOWNLOADS_DIR / f"{base_name}.opus"
    
    subprocess.run([
        "ffmpeg", "-y", "-i", str(source_path),
        "-vn", "-c:a", "libopus",
        "-application", "audio",
        "-b:a", "192k",
        "-compression_level", "10",
        "-vbr", "on",
        "-f", "ogg",
        str(opus_path)
    ], check=True, capture_output=True)
    
    # Cleanup temp file
    source_path.unlink(missing_ok=True)
    print(f"  ✓ Converted to {opus_path.name}")
    
    return True


def check_via_browser(state):
    """
    Check current versions via browser automation.
    Returns dict of track_name -> version, or None if check failed.
    
    Note: This requires the browser tab to be attached.
    The cron job should spawn an isolated session that:
    1. Opens the Samply page
    2. Extracts track versions from the snapshot
    3. Returns the results
    """
    # This is a placeholder - actual browser check would be done
    # by spawning a sub-agent with browser access
    pass


def compare_versions(old_tracks, current_versions):
    """Find tracks that have been updated."""
    changes = []
    for track in old_tracks:
        name = track["name"]
        if name in current_versions:
            if current_versions[name] > track["version"]:
                changes.append({
                    "track": track,
                    "old_version": track["version"],
                    "new_version": current_versions[name]
                })
    return changes


def main():
    state = load_state()
    
    # Check via browser (would be implemented as sub-agent)
    current_versions = check_via_browser(state)
    
    if current_versions is None:
        print("Could not check versions - browser tab may not be attached")
        sys.exit(1)
    
    changes = compare_versions(state["tracks"], current_versions)
    
    if changes:
        print(f"Found {len(changes)} updated track(s):")
        for change in changes:
            print(f"  {change['track']['name']}: v{change['old_version']} → v{change['new_version']}")
            
            # Update version in state
            for track in state["tracks"]:
                if track["name"] == change["track"]["name"]:
                    track["version"] = change["new_version"]
                    download_track(state, track)
                    track["downloaded"] = True
                    print(f"  ✓ Downloaded {track['name']}")
        
        save_state(state)
        print("\nUpdates complete!")
    else:
        print("No updates found")
        save_state(state)


if __name__ == "__main__":
    main()