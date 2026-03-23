#!/usr/bin/env python3
"""
Samply Update Checker
Checks for version updates via browser automation and downloads changed files.
Uses .env.samply or .env for configuration.
"""

import json
import os
import subprocess
import sys
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
PREFER_FLAC = os.getenv("SAMPLY_PREFER_FLAC", "true").lower() == "true"
OUTPUT_FORMAT = os.getenv("SAMPLY_OUTPUT_FORMAT", "opus")
OUTPUT_BITRATE = os.getenv("SAMPLY_OUTPUT_BITRATE", "192k")
MATRIX_ROOM = os.getenv("SAMPLY_MATRIX_ROOM", "")


def load_state():
    with open(STATE_FILE) as f:
        return json.load(f)


def save_state(state):
    state["last_check"] = datetime.now().isoformat()
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def get_cdn_url(state, file_id, quality="aac256k"):
    """Build CDN URL for a file.
    
    quality: 'aac256k', 'flac', or 'wav'
    """
    return f"{state['cdn_base']}/{file_id}/output/{quality}@output.mp4"


def download_track(state, track, prefer_flac=None):
    """Download and convert a track.
    
    If prefer_flac=True and FLAC is available, downloads FLAC version.
    Otherwise downloads AAC 256kbps version.
    Converts to configured output format (default: Opus 192kbps).
    """
    if prefer_flac is None:
        prefer_flac = PREFER_FLAC
        
    base_url = f"{state['cdn_base']}/{track['file_id']}/output"
    base_name = Path(track["name"]).stem
    
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
    
    # Determine output path based on format
    if OUTPUT_FORMAT == "opus":
        output_path = DOWNLOADS_DIR / f"{base_name}.opus"
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", str(source_path),
            "-vn", "-c:a", "libopus",
            "-application", "audio",
            "-b:a", OUTPUT_BITRATE,
            "-compression_level", "10",
            "-vbr", "on",
            "-f", "ogg",
            str(output_path)
        ]
    elif OUTPUT_FORMAT == "mp3":
        output_path = DOWNLOADS_DIR / f"{base_name}.mp3"
        # Map quality setting to MP3 VBR quality
        quality_map = {"192k": "2", "256k": "0", "320k": "0"}
        q_val = quality_map.get(OUTPUT_BITRATE, "2")
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", str(source_path),
            "-vn", "-c:a", "libmp3lame",
            "-q:a", q_val,
            str(output_path)
        ]
    elif OUTPUT_FORMAT == "flac":
        output_path = DOWNLOADS_DIR / f"{base_name}.flac"
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", str(source_path),
            "-vn", "-c:a", "flac",
            "-compression_level", "8",
            str(output_path)
        ]
    else:
        # Default to Opus
        output_path = DOWNLOADS_DIR / f"{base_name}.opus"
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", str(source_path),
            "-vn", "-c:a", "libopus",
            "-b:a", OUTPUT_BITRATE,
            "-f", "ogg",
            str(output_path)
        ]
    
    subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
    
    # Cleanup temp file
    source_path.unlink(missing_ok=True)
    print(f"  ✓ Converted to {output_path.name}")
    
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
    # Ensure downloads dir exists
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    
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
        
        # Add to history
        if "history" not in state:
            state["history"] = []
        for change in changes:
            state["history"].append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "change": f"{change['track']['name']} updated v{change['old_version']}→v{change['new_version']}"
            })
        
        save_state(state)
        print("\nUpdates complete!")
    else:
        print("No updates found")
        state["last_check"] = datetime.now().isoformat()
        state["last_check_status"] = f"v{state['tracks'][0]['version'] if state['tracks'] else '?'} (no change)"
        save_state(state)


if __name__ == "__main__":
    main()