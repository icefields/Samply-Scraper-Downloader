# Samply Track Downloader

A Python toolkit for tracking and downloading audio files from Samply project shares. Monitors for version updates and automatically downloads changed tracks.

## Table of Contents

- [Installation](#installation)
- [Dependencies](#dependencies)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Check for Updates](#check-for-updates)
  - [Display Status](#display-status)
  - [Browser Checker (Standalone)](#browser-checker-standalone)
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
- Chromium browser (system install or Playwright-managed)

### Install Python Dependencies

```bash
pip install python-dotenv playwright
playwright install chromium
```

**Note:** Playwright controls Chromium directly via DevTools Protocol — **no browser extensions needed**. It runs in headless mode (no visible window).

Or use your system Chromium (auto-detected):

```bash
# Arch Linux
sudo pacman -S chromium

# Debian/Ubuntu
sudo apt install chromium
```

### Clone and Setup

```bash
# Clone the repository
git clone https://github.com/icefields/Samply-Scraper-Downloader.git
cd Samply-Scraper-Downloader

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
| `chromium` | Browser automation (headless) | System package or `playwright install chromium` |

### Python Packages

| Package | Purpose | Version |
|---------|---------|---------|
| `python-dotenv` | Load environment variables from .env files | >=0.19.0 |
| `playwright` | Browser automation for version checking | >=1.40.0 |

---

## Quick Start

1. **Configure your project URL**

   ```bash
   # Edit .env and set your Samply share URL
   SAMPLY_URL=https://samply.app/p/YOUR_SHARE_ID
   ```

2. **Initialize the state file**

   Create `samply_tracker_state.json` with your project info:

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

   To find `user_id` and `file_id`, open your browser's DevTools (F12), go to the Network tab, and reload the Samply page. Look for API requests containing these IDs.

3. **Run the tracker**

   ```bash
   python3 samply_tracker.py
   ```

---

## Usage

### Check for Updates

The main script that checks for new versions and downloads updates:

```bash
# Check for updates using the URL from state file
python3 samply_check.py

# Output when no updates:
# No updates found

# Output when updates found:
# Found 1 updated track(s):
#   Sweet Fiend EP.mp3: v7 → v8
#   Downloaded FLAC source
#   ✓ Converted to Sweet Fiend EP.opus
#   ✓ Downloaded Sweet Fiend EP.mp3
#
# Updates complete!
```

**Force re-download all tracks:**

```bash
# Force re-download even if version hasn't changed
python3 samply_check.py --force

# Output:
# Force mode: re-downloading all 1 track(s)
#   Sweet Fiend EP.mp3 (v8)
#   Downloaded FLAC source
#   ✓ Converted to Sweet Fiend EP.opus
#   ✓ Downloaded Sweet Fiend EP.mp3
#
# Force download complete!
```

**What it does:**
1. Loads state from `samply_tracker_state.json`
2. Calls `samply_browser.py` to extract current versions from the Samply page
3. Compares with stored versions
4. Downloads any updated tracks from CDN
5. Converts to your configured output format (Opus/MP3/FLAC)
6. Updates the state file with new versions and history

### Display Status

Show the current status of tracked projects:

```bash
python3 samply_tracker.py

# Output:
# Samply Tracker - Sweet Fiend 2025
# Artist: Keegan Okazaki
# URL: https://samply.app/p/vK1BBYfLHbbSLee53OYW
#
# Tracks:
#   [✓ downloaded] Sweet Fiend EP.mp3 (v8) - 23:29
#
# Last check: 2026-03-23T16:20:18.101525
# Downloads: /home/user/Music/samply_downloads
```

This is a read-only operation — it doesn't check for updates or download anything.

### Browser Checker (Standalone)

You can run the browser checker independently to see what versions are currently on Samply:

```bash
# Check using URL from state file
python3 samply_browser.py --state samply_tracker_state.json

# Output:
# {"Sweet Fiend EP.mp3": 8}

# Check using direct URL
python3 samply_browser.py "https://samply.app/p/vK1BBYfLHbbSLee53OYW"

# Output:
# {"Sweet Fiend EP.mp3": 8}

# With custom timeout (default 60000ms)
python3 samply_browser.py --state samply_tracker_state.json --timeout 120000

# Output:
# {"Sweet Fiend EP.mp3": 8}
```

**What it does:**
1. Opens the Samply URL in headless Chromium
2. Waits 10 seconds for React to render the page
3. Extracts track names and version numbers from the DOM
4. Returns JSON to stdout

**Exit codes:**
- `0` — Success (JSON output)
- `1` — Error (JSON with `error` key)

### Manual Download

If you want to manually download a specific track:

```bash
# Download from CDN (AAC 256kbps)
curl -L -o "track.mp4" "https://cdn.samply.app/users/USER_ID/files/FILE_ID/output/aac256k@output.mp4"

# Or download FLAC (if available)
curl -L -o "track.mp4" "https://cdn.samply.app/users/USER_ID/files/FILE_ID/output/flac@output.mp4"

# Convert to your preferred format
ffmpeg -i track.mp4 -c:a libopus -b:a 192k track.opus
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
| `SAMPLY_OUTPUT_FORMAT` | No | `opus` | Output audio format (`opus`, `mp3`, `flac`) |
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

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         samply_check.py                                 │
│                       (Main Entry Point)                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. Load state from samply_tracker_state.json                          │
│                          │                                              │
│                          ▼                                              │
│  2. Call samply_browser.py ─────────────────────────────────────────┐  │
│                          │                                          │  │
│                          ▼                                          │  │
│  ┌───────────────────────────────────────────────────────────────┐   │  │
│  │                    samply_browser.py                           │   │  │
│  │                  (Browser Automation)                          │   │  │
│  ├───────────────────────────────────────────────────────────────┤   │  │
│  │  • Launch headless Chromium                                    │   │  │
│  │  • Navigate to Samply URL                                      │   │  │
│  │  • Wait 10 seconds for React render                            │   │  │
│  │  • Extract track names + versions from DOM                     │   │  │
│  │  • Return JSON: {"Track.mp3": 8}                               │   │  │
│  └───────────────────────────────────────────────────────────────┘   │  │
│                          │                                              │  │
│                          ▼                                              │
│  3. Compare versions with stored state                                 │
│                          │                                              │
│               ┌──────────┴──────────┐                                  │
│               ▼                     ▼                                  │
│          No changes            New version found                        │
│               │                     │                                   │
│               ▼                     ▼                                   │
│     Update timestamp        Download from CDN                          │
│     Save state                    │                                    │
│                                   ▼                                    │
│                          Convert to Opus/MP3/FLAC                       │
│                                   │                                    │
│                                   ▼                                    │
│                          Update state file                              │
│                                   │                                    │
│                                   ▼                                    │
│                          Append to history                               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### samply_browser.py

The browser automation component uses **Playwright** to:

1. Launch a headless Chromium browser
2. Navigate to the Samply share URL
3. Wait for React to render (10 seconds)
4. Extract track info from DOM elements
5. Return JSON to stdout

**Why Playwright?**

- Headless mode works on servers without GUI
- Automatically handles JavaScript rendering
- Supports multiple browser engines (Chromium, Firefox, WebKit)
- More reliable than Selenium for single-page apps

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
├── samply_browser.py       # Browser automation (Playwright)
├── samply_check.py         # Main checker + downloader
├── samply_tracker.py       # Status display (read-only)
├── samply_tracker_state.json  # State file
└── samply_downloads/       # Downloaded audio files
    ├── track1.opus
    ├── track2.opus
    └── ...
```

### Script Reference

| Script | Purpose | Dependencies |
|--------|---------|--------------|
| `samply_tracker.py` | Display project status | python-dotenv |
| `samply_check.py` | Check for updates + download | python-dotenv, ffmpeg, curl |
| `samply_browser.py` | Extract versions from page | playwright, chromium |

### samply_tracker.py

Read-only utility that displays project information:

```python
def main():
    state = load_state()
    print(f"Samply Tracker - {state.get('project_name', 'Unknown')}")
    print(f"Artist: {state.get('artist', 'Unknown')}")
    for track in state.get("tracks", []):
        status = "✓ downloaded" if track.get("downloaded") else "○ pending"
        print(f"  [{status}] {track['name']} (v{track['version']})")
```

### samply_check.py

Main checker that orchestrates the update process:

1. Calls `samply_browser.py` via subprocess
2. Parses JSON output
3. Compares versions
4. Downloads updated tracks
5. Converts to output format
6. Updates state file

### samply_browser.py

Browser automation using Playwright:

```python
def extract_versions(url: str, timeout: int = 60000) -> dict:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=timeout, wait_until="load")
        time.sleep(10)  # Wait for React
        
        track_items = page.query_selector_all("listitem")
        # ... extract track names and versions
        
        browser.close()
        return versions
```

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
  "last_check": "2026-03-23T16:20:18.101525",
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

---

## Output Formats

### Opus (Recommended)

Best quality-to-size ratio. Great for streaming and mobile devices.

- **Quality:** 192kbps VBR (configurable)
- **File size:** ~5MB per hour of audio
- **Compatibility:** All modern browsers, Android, Linux
- **Extension:** `.opus` (Ogg container)

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

### "playwright not installed"

```bash
pip install playwright
playwright install chromium
```

**No browser extensions required** — Playwright controls Chromium directly via Chrome DevTools Protocol.

### "Timeout loading page after 60000ms"

The Samply page is slow to load. Increase the timeout:

```bash
python3 samply_browser.py --state samply_tracker_state.json --timeout 120000
```

Or edit `samply_browser.py` and increase the `sleep(10)` wait time.

### "ffmpeg: command not found"

```bash
# Debian/Ubuntu
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Arch Linux
sudo pacman -S ffmpeg
```

### "Permission denied" when creating downloads directory

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
3. Verify the `file_id` matches current track versions

### FLAC download fails but AAC works

The uploader didn't provide a lossless source. This is normal — the script will automatically fall back to AAC.

### Empty JSON output from browser checker

The page might not have loaded in time. Try:

```bash
# Increase timeout and check with debug output
python3 samply_browser.py --state samply_tracker_state.json --timeout 120000 --debug
```

### State file corruption

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
git clone https://github.com/icefields/Samply-Scraper-Downloader.git
cd Samply-Scraper-Downloader

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install python-dotenv playwright
playwright install chromium

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

### Version 1.1.0 (2026-03-23)

- Added `samply_browser.py` with Playwright automation
- Implemented `check_via_browser()` functionality
- Browser uses system Chromium if available
- 10-second wait for React rendering
- Proper error handling and JSON output

### Version 1.0.0 (2026-03-23)

- Initial release
- Configurable via .env files
- Support for Opus, MP3, and FLAC output formats
- FLAC source preference with AAC fallback
- Version history tracking
- Automatic download and conversion pipeline