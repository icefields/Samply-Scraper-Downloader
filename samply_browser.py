#!/usr/bin/env python3
"""
Samply Browser Checker
Uses Playwright to extract current track versions from a Samply project page.
Called by samply_check.py, or can be run standalone.

Usage:
    python3 samply_browser.py <url>
    python3 samply_browser.py --url https://samply.app/p/SHARE_ID
    python3 samply_browser.py --state samply_tracker_state.json

Output:
    JSON to stdout: {"Sweet Fiend EP.mp3": 8, "Another.mp3": 3}
    Or error: {"error": "message"}
"""

import argparse
import json
import sys
import os
import time
from pathlib import Path

# Try to import playwright
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print(json.dumps({"error": "playwright not installed. Run: pip install playwright && playwright install chromium"}))
    sys.exit(1)


def extract_versions(url: str, timeout: int = 60000) -> dict:
    """
    Open Samply page and extract track versions.
    
    Args:
        url: Samply share URL (e.g., https://samply.app/p/SHARE_ID)
        timeout: Page load timeout in milliseconds
    
    Returns:
        Dict of {track_name: version} or {"error": message}
    """
    versions = {}
    
    try:
        with sync_playwright() as p:
            # Use system chromium if available
            chromium_path = "/usr/bin/chromium"
            if os.path.exists(chromium_path):
                browser = p.chromium.launch(
                    headless=True,
                    executable_path=chromium_path
                )
            else:
                browser = p.chromium.launch(headless=True)
            
            page = browser.new_page()
            
            # Navigate to the Samply page
            page.goto(url, timeout=timeout, wait_until="load")
            
            # Wait for React to render tracks
            time.sleep(5)
            
            # Find track elements - try multiple selectors
            track_items = page.query_selector_all("listitem")
            
            if not track_items:
                # Fallback: find elements containing .mp3
                track_items = page.query_selector_all("div:has-text('.mp3')")
            
            for item in track_items:
                text_content = item.inner_text()
                lines = text_content.strip().split('\n')
                
                track_name = None
                version = None
                
                for line in lines:
                    line = line.strip()
                    # Version is "v8" format (v + 1-4 digits)
                    if line.startswith('v') and len(line) <= 5 and line[1:].isdigit():
                        version = int(line[1:])
                    # Track name contains audio extension
                    elif '.mp3' in line or '.wav' in line or '.flac' in line:
                        track_name = line.strip('"\'')
                
                if track_name and version is not None:
                    versions[track_name] = version
            
            browser.close()
            
    except PlaywrightTimeout:
        return {"error": f"Timeout loading page after {timeout}ms"}
    except Exception as e:
        return {"error": str(e)}
    
    return versions


def main():
    parser = argparse.ArgumentParser(description="Extract track versions from Samply page")
    parser.add_argument("url", nargs="?", help="Samply share URL")
    parser.add_argument("--url", dest="url_flag", help="Samply share URL (alternative)")
    parser.add_argument("--timeout", type=int, default=60000, help="Page load timeout in ms (default: 60000)")
    parser.add_argument("--state", help="Path to state JSON file to extract URL")
    
    args = parser.parse_args()
    
    # Get URL from args or state file
    url = args.url or args.url_flag
    
    if not url and args.state:
        state_path = Path(args.state)
        if state_path.exists():
            with open(state_path) as f:
                state = json.load(f)
                url = state.get("url")
    
    if not url:
        print(json.dumps({"error": "No URL provided. Use: samply_browser.py <url> or --state <state.json>"}))
        sys.exit(1)
    
    result = extract_versions(url, timeout=args.timeout)
    print(json.dumps(result))
    
    if "error" in result:
        sys.exit(1)


if __name__ == "__main__":
    main()