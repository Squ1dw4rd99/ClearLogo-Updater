import json
import sys
import argparse
import requests

from plexapi.server import PlexServer
from plexapi.exceptions import NotFound, BadRequest

# --- Configuration ---
CONFIG_FILE = 'config.json'  # JSON file containing Plex URL and Token

def load_config():
    """Loads Plex URL and Token from the JSON config file."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            config_data = json.load(f)
        plex_url = config_data.get('plex_url')
        plex_token = config_data.get('plex_token')
        if not plex_url or not plex_token or plex_token == 'YOUR_plex_token_HERE':
            print(f"❌ Error: Ensure 'plex_url' and 'plex_token' are correctly set in {CONFIG_FILE}.")
            return None, None
        return plex_url.rstrip('/'), plex_token
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return None, None

def connect_plex(url, token):
    """Connects to the Plex server."""
    try:
        print(f"\n🔃 Connecting to Plex server at {url}...")
        plex = PlexServer(url, token, timeout=30)
        print(f"✅ Connected to Plex server: {plex.friendlyName} (Version: {plex.version})")
        return plex
    except Exception as e:
        print(f"❌ Error connecting to Plex server: {e}")
        return None

def search_titles(plex, query):
    """Search for titles in all libraries."""
    results = []
    for section in plex.library.sections():
        if section.type not in ['movie', 'show']:
            continue
        matches = section.search(query)
        for item in matches:
            results.append({
                'title': item.title,
                'year': getattr(item, 'year', ''),
                'type': section.type,
                'library': section.title,
                'item': item
            })
    return results

def select_from_results(results):
    """Prompt user to select a result from the search list."""
    if not results:
        print("❌ No results found.")
        return None
    print("\nSearch Results:")
    for idx, r in enumerate(results, 1):
        print(f"{idx}. {r['title']} ({r['year']}) [{r['type']}] - Library: {r['library']}")
    while True:
        choice = input(f"Select a title (1-{len(results)}) or 'q' to quit: ").strip()
        if choice.lower() == 'q':
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(results):
            return results[int(choice)-1]['item']
        print("Invalid selection. Try again.")

def get_clearlogo_url(item, plex_url, plex_token):
    """Get the full URL for the clearlogo image if it exists."""
    for image in getattr(item, 'images', []):
        if getattr(image, 'type', None) == 'clearLogo':
            # image.url is a relative path, e.g. '/library/metadata/10520/clearLogo/1757122405'
            full_url = f"{plex_url}{image.url}?X-Plex-Token={plex_token}"
            return full_url
    return None

def download_clearlogo(full_url, dest_path):
    """Download the clearlogo image from the full URL to the destination path."""
    try:
        response = requests.get(full_url, stream=True)
        if response.status_code == 200:
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print(f"✅ Logo downloaded to: {dest_path}")
            return True
        else:
            print(f"❌ Failed to download image. Status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error downloading image: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Get Plex ClearLogo URL")
    parser.add_argument('--search', '-s', type=str, help='Title to search for')
    args = parser.parse_args()

    plex_url, plex_token = load_config()
    if not plex_url or not plex_token:
        sys.exit(1)

    plex = connect_plex(plex_url, plex_token)
    if not plex:
        sys.exit(1)

    # Search for title
    query = args.search
    if not query:
        query = input("Enter the title to search for: ").strip()
    results = search_titles(plex, query)
    selected_item = select_from_results(results)
    if not selected_item:
        print("No item selected. Exiting.")
        sys.exit(0)

    print(f"\nSelected: {selected_item.title} ({getattr(selected_item, 'year', '')})")

    # Get clearlogo image URL from the selected item
    clearlogo_url = get_clearlogo_url(selected_item, plex_url, plex_token)
    if not clearlogo_url:
        print("❌ No clearlogo image found for this item.")
        sys.exit(0)

    print(f"\nClearLogo image URL:\n{clearlogo_url}")

    # Prompt if the user wants to search for another clearlogo
    again = input("Do you want to search for another ClearLogo? (y/n): ").strip().lower()
    if again == "y":
        main()
    else:
        print("Exiting.")

if __name__ == "__main__":
    main()