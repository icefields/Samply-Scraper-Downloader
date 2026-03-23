#!/usr/bin/env python3
"""
Samply Update Checker
Checks for version updates via browser automation and downloads changed files.
Uses .env.samply or .env for configuration.

Usage:
    python3 samply_check.py           # Download only updated tracks
    python3 samply_check.py -f        # Force re-download all tracks
    python3 samply_check.py --force   # Force re-download all tracks
"""

import argparse
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
COPY_DIR = Path(os.path.expanduser(os.getenv("SAMPLY_COPY_DIR", ""))) if os.getenv("SAMPLY_COPY_DIR") else None
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


def copy_to_destination(output_path):
    """Copy the output file to the destination directory if configured."""
    import shutil
    
    if not COPY_DIR:
        return
    
    COPY_DIR.mkdir(parents=True, exist_ok=True)
    dest_path = COPY_DIR / output_path.name
    shutil.copy2(output_path, dest_path)
    print(f"  ✓ Copied to {COPY_DIR}")


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
    
    # Copy to destination if configured
    copy_to_destination(output_path)
    
    return True


def check_via_browser(state):
    """
    Check current versions via browser automation.
    Returns dict of track_name -> version, or None if check failed.
    
    Calls samply_browser.py which uses Playwright to extract versions.
    """
    import subprocess
    
    url = state.get("url")
    if not url:
        print("No URL in state file")
        return None
    
    # Run the browser checker
    script_dir = Path(__file__).parent
    browser_script = script_dir / "samply_browser.py"
    
    result = subprocess.run(
        ["python3", str(browser_script), "--state", str(STATE_FILE)],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Browser check failed: {result.stderr}")
        return None
    
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"Failed to parse browser output: {e}")
        return None
    
    if "error" in data:
        print(f"Browser error: {data['error']}")
        return None
    
    return data


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
    # Parse arguments
    parser = argparse.ArgumentParser(description="Check for Samply updates and download changed tracks")
    parser.add_argument("-f", "--force", action="store_true", help="Force re-download all tracks regardless of version")
    args = parser.parse_args()
    
    # Ensure downloads dir exists
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    
    state = load_state()
    
    # Check via browser
    current_versions = check_via_browser(state)
    
    if current_versions is None:
        print("Could not check versions - browser check failed")
        sys.exit(1)
    
    if args.force:
        # Force mode: download all tracks regardless of version
        print(f"Force mode: re-downloading all {len(state['tracks'])} track(s)")
        for track in state["tracks"]:
            print(f"  {track['name']} (v{track['version']})")
            download_track(state, track)
            track["downloaded"] = True
            print(f"  ✓ Downloaded {track['name']}")
        
        # Add to history
        if "history" not in state:
            state["history"] = []
        state["history"].append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "change": f"Force re-downloaded all tracks"
        })
        
        save_state(state)
        print("\nForce download complete!")
    else:
        # Normal mode: only download updated tracks
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