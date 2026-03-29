import json
import re
import os

def remove_footnotes(text):
    """Remove Wikipedia footnote markers like [a], [16], [note 1]"""
    return re.sub(r'\[.*?\]', '', str(text)).strip()

def clean_entry(entry):
    """Normalize and clean a single game entry."""
    cleaned = {}

    # Unify 'game' and 'title' into one field called 'title'
    title = entry.get("title") or entry.get("game") or ""
    cleaned["title"] = remove_footnotes(title)

    # Unify 'platform(s)' and 'original platform(s)[a]' into 'platforms'
    platforms = entry.get("platform(s)") or entry.get("original platform(s)[a]") or ""
    cleaned["platforms"] = remove_footnotes(platforms)

    # Developer
    dev = entry.get("developer(s)") or entry.get("developer") or ""
    cleaned["developer"] = remove_footnotes(dev)

    # Publisher
    pub = entry.get("publisher(s)") or entry.get("publisher") or ""
    cleaned["publisher"] = remove_footnotes(pub)

    # Genre
    cleaned["genre"] = remove_footnotes(entry.get("genre", ""))

    # Year — extract 4-digit year only
    year_raw = entry.get("releaseyear") or entry.get("year") or ""
    year_match = re.search(r'\b(19|20)\d{2}\b', str(year_raw))
    cleaned["year"] = year_match.group(0) if year_match else ""

    # Sales (only present in best-selling list)
    cleaned["sales_millions"] = remove_footnotes(entry.get("sales(millions)", ""))

    # Source URL
    cleaned["source"] = entry.get("source", "")

    return cleaned

def is_valid(entry):
    title = entry.get("title", "")
    # Reject entries where title is just a number
    if re.match(r'^\d+$', title):
        return False
    return bool(title)

def deduplicate(entries):
    """Remove duplicate titles (keep first occurrence)."""
    seen = set()
    unique = []
    for e in entries:
        key = e["title"].lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(e)
    return unique

def clean(input_path="data/raw/games_raw.json",
          output_path="data/samples/games_clean.json"):

    with open(input_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    print(f"Raw entries: {len(raw)}")

    cleaned = [clean_entry(e) for e in raw]
    cleaned = [e for e in cleaned if is_valid(e)]
    cleaned = deduplicate(cleaned)

    os.makedirs("data/samples", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)

    print(f"Clean entries: {len(cleaned)}")
    print(f" Saved to {output_path}")
    print("\n📋 Sample cleaned entry:")
    print(json.dumps(cleaned[0], indent=2))

if __name__ == "__main__":
    clean()