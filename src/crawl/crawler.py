import requests
from bs4 import BeautifulSoup
import json
import time
import os
from tqdm import tqdm

# These pages have cleaner, more consistent tables
SEED_URLS = [
    "https://en.wikipedia.org/wiki/List_of_best-selling_video_games",
    "https://en.wikipedia.org/wiki/List_of_video_games_listed_among_the_best",
    "https://en.wikipedia.org/wiki/List_of_video_games_considered_the_best",
]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; videogame-kg/1.0; academic project)"}

def fetch_page(url):
    time.sleep(1)
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            return response.text
        else:
            print(f"  → HTTP {response.status_code}")
    except Exception as e:
        print(f"  → Error: {e}")
    return None

def parse_game_tables(html, source_url):
    soup = BeautifulSoup(html, "html.parser")
    games = []

    for table in soup.find_all("table", class_="wikitable"):
        # Get column headers
        header_row = table.find("tr")
        if not header_row:
            continue
        headers = [th.get_text(strip=True).lower() for th in header_row.find_all(["th", "td"])]
        if not headers:
            continue

        print(f"  → Table headers found: {headers[:6]}")  # show first 6 columns

        for row in table.find_all("tr")[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue

            game = {"source": source_url}
            for i, cell in enumerate(cells):
                if i < len(headers) and headers[i]:
                    game[headers[i]] = cell.get_text(strip=True)

            # Only save rows that have some real content
            if len(game) > 2:
                games.append(game)

    return games

def crawl(output_path="data/raw/games_raw.json"):
    all_games = []

    for url in tqdm(SEED_URLS, desc="Crawling Wikipedia pages"):
        print(f"\nFetching: {url}")
        html = fetch_page(url)
        if html:
            games = parse_game_tables(html, url)
            print(f"  → Total entries from this page: {len(games)}")
            all_games.extend(games)
        else:
            print(f"  → Failed to fetch page")

    os.makedirs("data/raw", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_games, f, indent=2, ensure_ascii=False)

    print(f"\n Done! {len(all_games)} total entries saved to {output_path}")
    if all_games:
        print("\n📋 Sample entry:")
        print(json.dumps(all_games[0], indent=2))

if __name__ == "__main__":
    crawl()