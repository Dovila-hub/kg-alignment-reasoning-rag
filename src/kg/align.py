import json
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, OWL, XSD
from SPARQLWrapper import SPARQLWrapper, JSON
import re
import time

VG = Namespace("http://videogame-kg.org/ontology#")
VGR = Namespace("http://videogame-kg.org/resource/")
WD = Namespace("http://www.wikidata.org/entity/")

def slugify(text):
    text = text.strip().replace(" ", "_")
    text = re.sub(r"[^\w_]", "", text)
    return text[:80]

def query_wikidata(name, entity_type="game"):
    """Search Wikidata for a matching entity by name."""
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    sparql.addCustomHttpHeader("User-Agent", "videogame-kg/1.0 (academic project)")

    if entity_type == "game":
        type_filter = "wd:Q7889"  # video game
    elif entity_type == "developer":
        type_filter = "wd:Q210167"  # video game developer
    else:
        type_filter = "wd:Q210167"

    query = f"""
    SELECT ?item ?itemLabel WHERE {{
      ?item wdt:P31 {type_filter} .
      ?item rdfs:label "{name}"@en .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT 1
    """
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)

    try:
        results = sparql.query().convert()
        bindings = results["results"]["bindings"]
        if bindings:
            return bindings[0]["item"]["value"]
    except Exception as e:
        print(f"    ⚠️  Wikidata error for '{name}': {e}")
    return None

def align(input_ttl="kg_artifacts/expanded.ttl",
          output_ttl="kg_artifacts/alignment.ttl",
          games_path="data/samples/games_clean.json"):

    g = Graph()
    g.parse(input_ttl, format="turtle")

    align_graph = Graph()
    align_graph.bind("vgr", VGR)
    align_graph.bind("owl", OWL)
    align_graph.bind("wd", WD)

    with open(games_path, "r", encoding="utf-8") as f:
        games = json.load(f)

    # Only align a sample to avoid hammering Wikidata
    sample_games = [g for g in games if g.get("title")][:15]
    sample_devs = list({g["developer"] for g in games
                        if g.get("developer") and g["developer"].lower() != "various"})[:10]

    aligned_count = 0

    print("🔗 Aligning games to Wikidata...")
    for game in sample_games:
        title = game["title"]
        print(f"  Searching: {title}")
        wd_uri = query_wikidata(title, "game")
        if wd_uri:
            local_uri = VGR[slugify(title)]
            align_graph.add((local_uri, OWL.sameAs, URIRef(wd_uri)))
            align_graph.add((local_uri, RDFS.label, Literal(title, datatype=XSD.string)))
            print(f"     Matched → {wd_uri}")
            aligned_count += 1
        else:
            print(f"     No match found")
        time.sleep(1)  # be polite to Wikidata

    print(f"\n🔗 Aligning developers to Wikidata...")
    for dev in sample_devs:
        print(f"  Searching: {dev}")
        wd_uri = query_wikidata(dev, "developer")
        if wd_uri:
            local_uri = VGR[slugify(dev)]
            align_graph.add((local_uri, OWL.sameAs, URIRef(wd_uri)))
            align_graph.add((local_uri, RDFS.label, Literal(dev, datatype=XSD.string)))
            print(f"     Matched → {wd_uri}")
            aligned_count += 1
        else:
            print(f"     No match found")
        time.sleep(1)

    align_graph.serialize(destination=output_ttl, format="turtle")
    print(f"\n Alignment done: {aligned_count} entities linked")
    print(f"   Saved to {output_ttl}")

if __name__ == "__main__":
    align()