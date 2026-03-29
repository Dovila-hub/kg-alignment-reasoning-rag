import json
import spacy
import os

nlp = spacy.load("en_core_web_sm")

def extract_entities(text):
    """Run spaCy NER on a piece of text and return found entities."""
    doc = nlp(text)
    return [{"text": ent.text, "label": ent.label_} for ent in doc.ents]

def build_text_for_game(game):
    """Combine game fields into a sentence for NER."""
    parts = []
    if game.get("title"):
        parts.append(game["title"])
    if game.get("developer"):
        parts.append(f"developed by {game['developer']}")
    if game.get("publisher"):
        parts.append(f"published by {game['publisher']}")
    if game.get("platforms"):
        parts.append(f"on {game['platforms']}")
    if game.get("year"):
        parts.append(f"in {game['year']}")
    return ", ".join(parts) + "."

def run_ner(input_path="data/samples/games_clean.json",
            output_path="data/samples/games_ner.json"):

    with open(input_path, "r", encoding="utf-8") as f:
        games = json.load(f)

    results = []
    for game in games:
        text = build_text_for_game(game)
        entities = extract_entities(text)
        results.append({**game, "ner_input": text, "entities": entities})

    os.makedirs("data/samples", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"✅ NER done for {len(results)} games → {output_path}")
    print("\n📋 Sample NER output:")
    sample = results[10]  # pick a more interesting entry
    print(f"  Text : {sample['ner_input']}")
    print(f"  Entities:")
    for ent in sample["entities"]:
        print(f"    [{ent['label']}] {ent['text']}")

    # --- Ambiguity cases for the report ---
    print("\n⚠️  Ambiguity Cases:")

    ambiguity_cases = [
        {
            "case": "1 - 'Nintendo' as ORG vs part of platform name",
            "example": "Super Mario Bros., developed by Nintendo, on Nintendo Entertainment System, in 1985.",
        },
        {
            "case": "2 - Year as DATE vs cardinal number",
            "example": "Grand Theft Auto V, developed by Rockstar North, published by Rockstar Games, in 2013.",
        },
        {
            "case": "3 - 'Various' misidentified as a named entity",
            "example": "Tetris, developed by Various, published by Various, on Multi-platform, in 1988.",
        },
    ]

    for ac in ambiguity_cases:
        doc = nlp(ac["example"])
        print(f"\n  Case {ac['case']}")
        print(f"  Text: {ac['example']}")
        print(f"  Entities found:")
        for ent in doc.ents:
            print(f"    [{ent.label_}] {ent.text}")

if __name__ == "__main__":
    run_ner()