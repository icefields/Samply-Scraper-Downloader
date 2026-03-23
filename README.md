# Samply Track Downloader

A Python toolkit for tracking and downloading audio files from Samply project shares. Monitors for version updates and automatically downloads changed tracks.

## Table of Contents

- [Installation](#installation)
- [Dependencies](#dependencies)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Configuration](#configuration)
- [How It Works](#how-it-works)
- [Code Architecture](#code-architecture)
- [State File Format](#state-file-format)
- [Output Formats](#output-formats)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Installation

### Prerequisites

- Python 3.8 or higher
- `ffmpeg` installed and available in your PATH
- `curl` installed and available in your PATH

### Install Python Dependencies

```bash
pip install python-dotenv playwright
playwright install chromium
```

### Clone and Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/SamplyScraperDownloader.git
cd SamplyScraperDownloader

# Create your configuration
cp .env-example .env

# Edit .env with your project details
$EDITOR .env

# Create downloads directory (if not exists)
mkdir -p ~/Music/samply_downloads
```

---

## Dependencies

### Required System Tools

| Tool | Purpose | Installation |
|------|---------|--------------|
| `ffmpeg` | Audio conversion and encoding | `sudo apt install ffmpeg` (Debian/Ubuntu) or `brew install ffmpeg` (macOS) |
| `curl` | Downloading files from CDN | Usually pre-installed on most systems |

### Python Packages

| Package | Purpose | Version |
|---------|---------|---------|
| `python-dotenv` | Load environment variables from .env files | >=0.19.0 |
| `playwright` | Browser automation for version checking | >=1.40.0 |

### Installing Playwright

After installing the Python package, you must install the browser:

```bash
pip install playwright
playwright install chromium
```

Or use your system's Chromium (the script will auto-detect `/usr/bin/chromium`):

```bash
# Arch Linux
sudo pacman -S chromium

# Debian/Ubuntu
sudo apt install chromium
```
# Arch Linux
sudo pacman -S chromium

# Debian/Ubuntu
sudo apt install chromium
```

---

## Quick Start

1. **Configure your project URL**

   ```bash
   # Edit .env and set your Samply share URL
   SAMPLY_URL=https://samply.app/p/YOUR_SHARE_ID
   ```

2. **Initialize the state file**

   You'll need to create `samply_tracker_state.json` with your project info:

   ```json
   {
     "url": "https://samply.app/p/YOUR_SHARE_ID",
     "share_id": "YOUR_SHARE_ID",
     "user_id": "USER_ID_FROM_NETWORK_REQUEST",
     "project_name": "Your Project Name",
     "artist": "Artist Name",
     "cdn_base": "https://cdn.samply.app/users/USER_ID/files",
     "tracks": [
       {
         "name": "Track Name.mp3",
         "version": 1,
         "duration": "3:45",
         "file_id": "FILE_UUID",
         "downloaded": false
       }
     ]
   }
   ```

3. **Run the tracker**

   ```bash
   python3 samply_tracker.py
   ```

---

## Usage

### Display Project Status

```bash
python3 samply_tracker.py
```

Output:
```
Samply Tracker - Project Name
Artist: Artist Name
URL: https://samply.app/p/SHARE_ID

Tracks:
  [✓ downloaded] Track One.mp3 (v5) - 4:32
  [○ pending] Track Two.mp3 (v3) - 3:21

Last check: 2026-03-23T14:49:00-04:00
Downloads: /home/user/Music/samply_downloads
```

### Check for Updates

```bash
python3 samply_check.py
```

This script:
1. Connects to the Samply page via browser automation
2. Extracts current track versions
3. Downloads any updated tracks
4. Converts to your preferred output format
5. Updates the state file

### Manual Download

If you want to manually download a specific track, you can use the CDN URL pattern:

```bash
# Replace USER_ID and FILE_ID with actual values
curl -L -o "track.mp4" "https://cdn.samply.app/users/USER_ID/files/FILE_ID/output/aac256k@output.mp4"
ffmpeg -i track.mp4 -c:a libmp3lame -q:a 2 track.mp3
```

---

## Configuration

Configuration is handled via environment variables, loaded from two files in order:

1. `.env` — User overrides (gitignored, create from `.env-example`)
2. `.env.samply` — Default values shipped with the project

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SAMPLY_URL` | Yes | — | The Samply project share URL |
| `SAMPLY_PROJECT_NAME` | No | `"Unknown"` | Display name for the project |
| `SAMPLY_ARTIST` | No | `"Unknown"` | Artist/creator name |
| `SAMPLY_DOWNLOADS_DIR` | No | `./samply_downloads` | Directory for downloaded files |
| `SAMPLY_STATE_FILE` | No | `./samply_tracker_state.json` | Path to state file |
| `SAMPLY_PREFER_FLAC` | No | `true` | Download FLAC source when available |
| `SAMPLY_OUTPUT_FORMAT` | No | `opus` | Output audio format |
| `SAMPLY_OUTPUT_BITRATE` | No | `192k` | Bitrate for lossy formats |
| `SAMPLY_MATRIX_ROOM` | No | `""` | Matrix room for notifications (optional) |

### Example .env File

```bash
# Project Configuration
SAMPLY_URL=https://samply.app/p/ABC123xyz
SAMPLY_PROJECT_NAME=My Album 2024
SAMPLY_ARTIST=My Band Name

# Paths
SAMPLY_DOWNLOADS_DIR=~/Music/samply_downloads
SAMPLY_STATE_FILE=~/.config/samply/state.json

# Audio Quality
SAMPLY_PREFER_FLAC=true
SAMPLY_OUTPUT_FORMAT=opus
SAMPLY_OUTPUT_BITRATE=192k
```

---

## How It Works

### Overview

Samply is a music collaboration platform that allows artists to share works-in-progress with collaborators. Projects are shared via unique URLs (e.g., `https://samply.app/p/SHARE_ID`). Each project contains one or more tracks, and tracks can be updated by the artist with new versions.

This tool:

1. **Tracks versions** — Monitors the version numbers of each track in a project
2. **Downloads updates** — When a track version changes, downloads the new version
3. **Converts formats** — Converts from Samply's source format to your preferred output
4. **Maintains history** — Keeps a record of all version changes

### Samply CDN Architecture

Samply stores audio files on a CDN with the following URL pattern:

```
https://cdn.samply.app/users/{USER_ID}/files/{FILE_ID}/output/{QUALITY}@output.mp4
```

Where:
- `{USER_ID}` — The Samply user ID (extracted from network requests)
- `{FILE_ID}` — UUID for each track file
- `{QUALITY}` — One of: `aac256k`, `flac`, `wav`

The `aac256k` quality is always available. FLAC availability depends on whether the uploader provided a lossless source.

### Version Tracking

Samply displays version numbers for each track in the web UI. The browser automation component:

1. Opens the Samply share URL
2. Waits for the page to load
3. Extracts version numbers from the DOM
4. Returns a dict of `{track_name: version}`

The checker compares these versions against the stored state and identifies which tracks have been updated.

### Download Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      samply_check.py                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Load state from SAMPLY_STATE_FILE                       │
│                    │                                        │
│                    ▼                                        │
│  2. Check current versions via browser                      │
│                    │                                        │
│                    ▼                                        │
│  3. Compare with stored versions                            │
│                    │                                        │
│          ┌────────┴────────┐                               │
│          ▼                 ▼                               │
│     No changes         New version                          │
│          │                 │                               │
│          ▼                 ▼                               │
│     Update timestamp   Download from CDN                    │
│                              │                              │
│                              ▼                              │
│                        Convert format                        │
│                              │                              │
│                              ▼                              │
│                        Update state file                     │
│                              │                              │
│                              ▼                              │
│                        Append to history                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Code Architecture

### File Structure

```
SamplyScraperDownloader/
├── .env                    # User configuration (gitignored)
├── .env-example            # Template with documentation
├── .env.samply             # Default configuration
├── .git/                   # Git repository
├── README.md               # This file
├── samply_check.py         # Main checker script
├── samply_tracker.py       # Status display script
├── samply_tracker_state.json  # State file
└── samply_downloads/       # Downloaded audio files
    ├── track1.opus
    ├── track2.opus
    └── ...
```

### samply_tracker.py

The `samply_tracker.py` script is a read-only utility that displays the current status of tracked projects.

#### Module Imports

```python
import json
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
```

| Module | Purpose |
|--------|---------|
| `json` | Parse and write state file |
| `os` | Environment variable access |
| `datetime` | Timestamp handling |
| `pathlib.Path` | Cross-platform path operations |
| `dotenv.load_dotenv` | Load .env configuration files |

#### Configuration Loading

The script loads configuration in a two-pass approach:

```python
env_path = Path(__file__).parent
load_dotenv(env_path / ".env", override=True)      # User config first
load_dotenv(env_path / ".env.samply")               # Defaults as fallback
```

This ensures user settings in `.env` take precedence over defaults in `.env.samply`.

#### Path Expansion

```python
STATE_FILE = Path(os.path.expanduser(os.getenv("SAMPLY_STATE_FILE", ...)))
DOWNLOADS_DIR = Path(os.path.expanduser(os.getenv("SAMPLY_DOWNLOADS_DIR", ...)))
```

The `os.path.expanduser()` call converts `~` to the home directory path, allowing users to write:

```bash
SAMPLY_DOWNLOADS_DIR=~/Music/samply_downloads
```

Instead of:

```bash
SAMPLY_DOWNLOADS_DIR=/home/username/Music/samply_downloads
```

#### State Management

```python
def load_state():
    with open(STATE_FILE) as f:
        return json.load(f)

def save_state(state):
    state["last_check"] = datetime.now().isoformat()
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)
```

State is stored as JSON with human-readable formatting (`indent=2`). The `last_check` timestamp is updated on every save.

#### Main Function

```python
def main():
    state = load_state()
    
    # Display project info from state or environment
    print(f"Samply Tracker - {state.get('project_name', os.getenv('SAMPLY_PROJECT_NAME', 'Unknown'))}")
    print(f"Artist: {state.get('artist', os.getenv('SAMPLY_ARTIST', 'Unknown'))}")
    print(f"URL: {state.get('url', os.getenv('SAMPLY_URL', 'N/A'))}")
    
    # List tracks with status
    for track in state.get("tracks", []):
        status = "✓ downloaded" if track.get("downloaded") else "○ pending"
        print(f"  [{status}] {track['name']} (v{track['version']}) - {track.get('duration', '?')}")
    
    # Show last check and downloads path
    print(f"Last check: {state.get('last_check', 'never')}")
    print(f"Downloads: {DOWNLOADS_DIR}")
```

The display prioritizes state file values over environment variables, allowing per-project overrides.

---

### samply_check.py

The `samply_check.py` script performs the actual update checking and downloading.

#### Additional Configuration

```python
PREFER_FLAC = os.getenv("SAMPLY_PREFER_FLAC", "true").lower() == "true"
OUTPUT_FORMAT = os.getenv("SAMPLY_OUTPUT_FORMAT", "opus")
OUTPUT_BITRATE = os.getenv("SAMPLY_OUTPUT_BITRATE", "192k")
```

These variables control audio quality preferences:
- `PREFER_FLAC`: Whether to attempt FLAC download first
- `OUTPUT_FORMAT`: Target format (`opus`, `mp3`, or `flac`)
- `OUTPUT_BITRATE`: Quality setting for lossy formats

#### CDN URL Construction

```python
def get_cdn_url(state, file_id, quality="aac256k"):
    """Build CDN URL for a file.
    
    quality: 'aac256k', 'flac', or 'wav'
    """
    return f"{state['cdn_base']}/{file_id}/output/{quality}@output.mp4"
```

The `cdn_base` is derived from the user ID and stored in the state file:

```
https://cdn.samply.app/users/{USER_ID}/files/{FILE_ID}/output/{QUALITY}@output.mp4
```

#### Download Function

The `download_track()` function handles the complete download and conversion pipeline:

```python
def download_track(state, track, prefer_flac=None):
    """Download and convert a track.
    
    If prefer_flac=True and FLAC is available, downloads FLAC version.
    Otherwise downloads AAC 256kbps version.
    Converts to configured output format (default: Opus 192kbps).
    """
```

##### Step 1: Determine FLAC Preference

```python
if prefer_flac is None:
    prefer_flac = PREFER_FLAC
```

Allows overriding the global setting per-call.

##### Step 2: Try FLAC Download

```python
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
```

The `-f` flag makes curl fail silently on HTTP errors, allowing graceful fallback to AAC.

##### Step 3: Fallback to AAC

```python
if not source_path:
    aac_url = f"{base_url}/aac256k@output.mp4"
    aac_path = DOWNLOADS_DIR / f"{track['file_id']}_aac.mp4"
    subprocess.run(["curl", "-L", "-o", str(aac_path), aac_url], check=True, capture_output=True)
    source_path = aac_path
    print(f"  Downloaded AAC source")
```

AAC 256kbps is always available as a fallback.

##### Step 4: Convert to Output Format

The function supports three output formats with appropriate ffmpeg parameters:

**Opus (default):**
```python
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
```

- `-vn`: No video (strip any video stream)
- `-c:a libopus`: Use Opus codec
- `-application audio`: Optimize for music
- `-compression_level 10`: Maximum compression (slower encoding)
- `-vbr on`: Variable bitrate for better quality/size ratio

**MP3:**
```python
ffmpeg_cmd = [
    "ffmpeg", "-y", "-i", str(source_path),
    "-vn", "-c:a", "libmp3lame",
    "-q:a", q_val,  # VBR quality (0=best, 9=worst)
    str(output_path)
]
```

Quality mapping:
| Bitrate | MP3 Quality (`-q:a`) |
|---------|---------------------|
| 128k | 4 |
| 192k | 2 |
| 256k | 1 |
| 320k | 0 |

**FLAC:**
```python
ffmpeg_cmd = [
    "ffmpeg", "-y", "-i", str(source_path),
    "-vn", "-c:a", "flac",
    "-compression_level", "8",
    str(output_path)
]
```

FLAC is lossless, so bitrate doesn't apply. Compression level 8 is maximum.

##### Step 5: Cleanup

```python
source_path.unlink(missing_ok=True)
print(f"  ✓ Converted to {output_path.name}")
```

Remove the temporary MP4 download file after successful conversion.

#### Browser Check Function

```python
def check_via_browser(state):
    """
    Check current versions via browser automation.
    Returns dict of track_name -> version, or None if check failed.
    """
    # Placeholder - actual implementation uses OpenClaw browser automation
    pass
```

This is a placeholder for the browser automation component. When run as an OpenClaw cron job, the agent:

1. Opens the Samply URL in a browser
2. Takes a snapshot of the page
3. Extracts version numbers from track elements
4. Returns the current versions

The function signature returns `dict[str, int]` where keys are track names and values are version numbers.

#### Version Comparison

```python
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
```

Returns a list of changed tracks with old and new versions.

#### Main Check Loop

```python
def main():
    # Ensure downloads directory exists
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    
    state = load_state()
    current_versions = check_via_browser(state)
    
    if current_versions is None:
        print("Could not check versions - browser tab may not be attached")
        sys.exit(1)
    
    changes = compare_versions(state["tracks"], current_versions)
    
    if changes:
        for change in changes:
            # Update version in state
            for track in state["tracks"]:
                if track["name"] == change["track"]["name"]:
                    track["version"] = change["new_version"]
                    download_track(state, track)
                    track["downloaded"] = True
        
        # Add to history
        for change in changes:
            state["history"].append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "change": f"{change['track']['name']} updated v{change['old_version']}→v{change['new_version']}"
            })
        
        save_state(state)
```

The history feature maintains a log of all version changes for reference.

---

## State File Format

The state file (`samply_tracker_state.json`) stores all project information:

```json
{
  "url": "https://samply.app/p/SHARE_ID",
  "share_id": "SHARE_ID",
  "user_id": "USER_UUID",
  "project_name": "Project Name",
  "artist": "Artist Name",
  "cdn_base": "https://cdn.samply.app/users/USER_UUID/files",
  "tracks": [
    {
      "name": "Track Name.mp3",
      "version": 5,
      "duration": "4:32",
      "file_id": "FILE_UUID",
      "downloaded": true
    }
  ],
  "last_check": "2026-03-23T14:49:00-04:00",
  "last_check_status": "v5 (no change)",
  "history": [
    {
      "date": "2026-03-21",
      "change": "Track Name updated v4→v5"
    }
  ]
}
```

### Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `url` | string | Full Samply share URL |
| `share_id` | string | URL path component after `/p/` |
| `user_id` | string | Samply user UUID (from network requests) |
| `project_name` | string | Display name for the project |
| `artist` | string | Artist/creator name |
| `cdn_base` | string | CDN URL prefix including user ID |
| `tracks` | array | List of track objects |
| `tracks[].name` | string | Track filename |
| `tracks[].version` | integer | Current version number |
| `tracks[].duration` | string | Duration in `M:SS` or `H:MM:SS` format |
| `tracks[].file_id` | string | CDN file UUID |
| `tracks[].downloaded` | boolean | Whether the track has been downloaded |
| `last_check` | string | ISO 8601 timestamp of last check |
| `last_check_status` | string | Human-readable status message |
| `history` | array | Log of version changes |

### Initial Setup

To track a new project, you need to:

1. **Find the share URL** — Open the Samply link in your browser
2. **Extract user_id** — Open browser dev tools, Network tab, reload page, find API requests
3. **Get track file_ids** — Same network requests will show track UUIDs
4. **Create the state file** with this information

Example network request showing file IDs:

```
GET /api/projects/{PROJECT_ID}/tracks
Response: [
  {
    "id": "56601b22-6019-448e-a348-12959e68f436",
    "name": "My Track",
    "version": 5,
    "duration": "3:45"
  }
]
```

---

## Output Formats

### Opus (Recommended)

Best quality-to-size ratio. Great for streaming and mobile devices.

- **Quality:** 192kbps VBR (configurable)
- **File size:** ~5MB per hour of audio
- **Compatibility:** All modern browsers, Android, Linux
- **Extension:** `.opus` (actually Ogg container)

```bash
SAMPLY_OUTPUT_FORMAT=opus
SAMPLY_OUTPUT_BITRATE=192k
```

### MP3

Universal compatibility. Every device plays MP3.

- **Quality:** VBR (quality 0-4, configurable via bitrate)
- **File size:** ~7MB per hour at quality 2
- **Compatibility:** Everything
- **Extension:** `.mp3`

```bash
SAMPLY_OUTPUT_FORMAT=mp3
SAMPLY_OUTPUT_BITRATE=192k
```

### FLAC

Lossless compression. Largest files, perfect quality.

- **Quality:** Lossless (identical to source)
- **File size:** ~30MB per hour
- **Compatibility:** Most music players, not web browsers
- **Extension:** `.flac`

```bash
SAMPLY_OUTPUT_FORMAT=flac
```

---

## Troubleshooting

### "Could not check versions - browser tab may not be attached"

The browser automation component requires an attached browser. This error means:

1. Running standalone without OpenClaw browser automation
2. Browser session expired or was closed

**Solution:** Run within OpenClaw cron job context, or implement your own browser automation.

### "ffmpeg: command not found"

FFmpeg is required for audio conversion.

**Solution:**
```bash
# Debian/Ubuntu
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Arch Linux
sudo pacman -S ffmpeg
```

### "Permission denied" when creating downloads directory

The script doesn't have permission to create the output directory.

**Solution:**
```bash
# Create directory manually with correct permissions
mkdir -p ~/Music/samply_downloads

# Or use a directory you have write access to
SAMPLY_DOWNLOADS_DIR=/home/youruser/samply_downloads
```

### Downloads fail with 403 Forbidden

The CDN may have expired the file or rate-limited requests.

**Solutions:**
1. Wait a few minutes and retry
2. Check if the Samply share link is still valid
3. Verify the file_id matches current track versions

### FLAC download fails but AAC works

The uploader didn't provide a lossless source.

**Solution:** This is normal. The script will automatically fall back to AAC.

### State file corruption

If the state file becomes corrupted:

```bash
# Backup corrupted file
mv samply_tracker_state.json samply_tracker_state.json.bak

# Reinitialize from current Samply project
# You'll need to extract user_id and file_ids from browser network requests
```

---

## Contributing

### Development Setup

```bash
# Clone repository
git clone https://github.com/yourusername/SamplyScraperDownloader.git
cd SamplyScraperDownloader

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install python-dotenv

# Run tests (if available)
python -m pytest
```

### Code Style

- Follow PEP 8
- Use type hints for function parameters and returns
- Document all functions with docstrings
- Keep functions focused on single responsibility

### Pull Requests

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit pull request with description of changes

---

## License

MIT License — See LICENSE file for details.

---

## Changelog

### Version 1.0.0 (2026-03-23)

- Initial release
- Configurable via .env files
- Support for Opus, MP3, and FLAC output formats
- FLAC source preference with AAC fallback
- Version history tracking
- Automatic download and conversion pipeline