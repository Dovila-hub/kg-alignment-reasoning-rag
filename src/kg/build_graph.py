import json
import re
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, OWL, XSD

# --- Namespaces ---
VG = Namespace("http://videogame-kg.org/ontology#")
VGR = Namespace("http://videogame-kg.org/resource/")

def slugify(text):
    """Convert a string to a safe URI slug."""
    text = text.strip().replace(" ", "_")
    text = re.sub(r"[^\w_]", "", text)
    return text[:80]  # cap length

def build_graph(input_path="data/samples/games_clean.json",
                output_ttl="kg_artifacts/expanded.ttl",
                output_nt="kg_artifacts/expanded.nt"):

    g = Graph()
    g.bind("vg", VG)
    g.bind("vgr", VGR)
    g.bind("owl", OWL)
    g.bind("xsd", XSD)

    # Load ontology
    g.parse("kg_artifacts/ontology.ttl", format="turtle")

    with open(input_path, "r", encoding="utf-8") as f:
        games = json.load(f)

    for game in games:
        title = game.get("title", "").strip()
        if not title:
            continue

        game_uri = VGR[slugify(title)]

        # Type
        g.add((game_uri, RDF.type, VG.Game))

        # Title
        g.add((game_uri, VG.hasTitle, Literal(title, datatype=XSD.string)))

        # Year
        year = game.get("year", "").strip()
        if year and year.isdigit():
            g.add((game_uri, VG.releaseYear, Literal(year, datatype=XSD.gYear)))

        # Sales
        sales = game.get("sales_millions", "").strip()
        try:
            g.add((game_uri, VG.salesMillions, Literal(float(sales), datatype=XSD.float)))
        except (ValueError, TypeError):
            pass

        # Developer
        dev = game.get("developer", "").strip()
        if dev and dev.lower() not in ("various", ""):
            dev_uri = VGR[slugify(dev)]
            g.add((dev_uri, RDF.type, VG.Developer))
            g.add((dev_uri, RDFS.label, Literal(dev, datatype=XSD.string)))
            g.add((game_uri, VG.hasDeveloper, dev_uri))

        # Publisher
        pub = game.get("publisher", "").strip()
        if pub and pub.lower() not in ("various", ""):
            pub_uri = VGR[slugify(pub)]
            g.add((pub_uri, RDF.type, VG.Publisher))
            g.add((pub_uri, RDFS.label, Literal(pub, datatype=XSD.string)))
            g.add((game_uri, VG.hasPublisher, pub_uri))

        # Platforms (can be comma-separated)
        platforms = game.get("platforms", "").strip()
        for plat in platforms.split(","):
            plat = plat.strip()
            if plat and plat.lower() != "multi-platform":
                plat_uri = VGR[slugify(plat)]
                g.add((plat_uri, RDF.type, VG.Platform))
                g.add((plat_uri, RDFS.label, Literal(plat, datatype=XSD.string)))
                g.add((game_uri, VG.hasPlatform, plat_uri))

        # Genre (can be comma-separated)
        genre = game.get("genre", "").strip()
        for g_name in genre.split(","):
            g_name = g_name.strip()
            if g_name:
                genre_uri = VGR[slugify(g_name)]
                g.add((genre_uri, RDF.type, VG.Genre))
                g.add((genre_uri, RDFS.label, Literal(g_name, datatype=XSD.string)))
                g.add((game_uri, VG.hasGenre, genre_uri))

    # Save in two formats
    g.serialize(destination=output_ttl, format="turtle")
    g.serialize(destination=output_nt, format="nt")

    print(f" Graph built with {len(g)} triples")
    print(f"   Saved to {output_ttl}")
    print(f"   Saved to {output_nt}")

    # KB Statistics
    games_count = len(set(g.subjects(RDF.type, VG.Game)))
    devs_count = len(set(g.subjects(RDF.type, VG.Developer)))
    pubs_count = len(set(g.subjects(RDF.type, VG.Publisher)))
    plats_count = len(set(g.subjects(RDF.type, VG.Platform)))
    genres_count = len(set(g.subjects(RDF.type, VG.Genre)))

    print(f"\n KB Statistics:")
    print(f"   Games      : {games_count}")
    print(f"   Developers : {devs_count}")
    print(f"   Publishers : {pubs_count}")
    print(f"   Platforms  : {plats_count}")
    print(f"   Genres     : {genres_count}")
    print(f"   Total triples: {len(g)}")

if __name__ == "__main__":
    build_graph()