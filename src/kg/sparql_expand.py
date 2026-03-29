from rdflib import Graph, Namespace
import json
import os

VG = Namespace("http://videogame-kg.org/ontology#")
VGR = Namespace("http://videogame-kg.org/resource/")

def run_sparql_queries(input_ttl="kg_artifacts/expanded.ttl"):

    g = Graph()
    g.parse(input_ttl, format="turtle")
    print(f" Graph loaded: {len(g)} triples\n")

    queries = {
        "1 - All games and their genres": """
            PREFIX vg: <http://videogame-kg.org/ontology#>
            SELECT ?title ?genre WHERE {
                ?game vg:hasTitle ?title .
                ?game vg:hasGenre ?g .
                ?g <http://www.w3.org/2000/01/rdf-schema#label> ?genre .
            }
            ORDER BY ?title
            LIMIT 10
        """,
        "2 - Games by developer": """
            PREFIX vg: <http://videogame-kg.org/ontology#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?title ?developer WHERE {
                ?game vg:hasTitle ?title .
                ?game vg:hasDeveloper ?dev .
                ?dev rdfs:label ?developer .
            }
            ORDER BY ?developer
            LIMIT 10
        """,
        "3 - Games released after 2015": """
            PREFIX vg: <http://videogame-kg.org/ontology#>
            SELECT ?title ?year WHERE {
                ?game vg:hasTitle ?title .
                ?game vg:releaseYear ?year .
                FILTER(xsd:integer(?year) > 2015)
            }
            ORDER BY DESC(?year)
            LIMIT 10
        """,
        "4 - Publishers with more than 2 games": """
            PREFIX vg: <http://videogame-kg.org/ontology#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?publisher (COUNT(?game) AS ?count) WHERE {
                ?game vg:hasPublisher ?pub .
                ?pub rdfs:label ?publisher .
            }
            GROUP BY ?publisher
            HAVING (COUNT(?game) > 2)
            ORDER BY DESC(?count)
        """,
        "5 - Self-published games (dev = pub)": """
            PREFIX vg: <http://videogame-kg.org/ontology#>
            SELECT ?title ?org WHERE {
                ?game vg:hasTitle ?title .
                ?game vg:hasDeveloper ?org .
                ?game vg:hasPublisher ?org .
            }
        """,
    }

    results_summary = {}

    for name, query in queries.items():
        print(f"{'='*50}")
        print(f"Query {name}")
        print(f"{'='*50}")
        try:
            results = list(g.query(query))
            print(f"  → {len(results)} results")
            for row in results[:5]:
                print(f"     {' | '.join(str(v) for v in row)}")
            if len(results) > 5:
                print(f"     ... and {len(results)-5} more")
            results_summary[name] = len(results)
        except Exception as e:
            print(f"  → Error: {e}")
        print()

    # Save schema summary for RAG step
    schema_summary = {
        "classes": ["Game", "Developer", "Publisher", "Platform", "Genre"],
        "properties": {
            "hasTitle": "Game → string",
            "releaseYear": "Game → year",
            "salesMillions": "Game → float",
            "hasDeveloper": "Game → Developer",
            "hasPublisher": "Game → Publisher",
            "hasPlatform": "Game → Platform",
            "hasGenre": "Game → Genre",
        },
        "namespace": "http://videogame-kg.org/ontology#",
        "resource_ns": "http://videogame-kg.org/resource/",
        "total_triples": len(g),
        "sample_queries": results_summary,
    }

    os.makedirs("kg_artifacts", exist_ok=True)
    with open("kg_artifacts/schema_summary.json", "w") as f:
        json.dump(schema_summary, f, indent=2)

    print(f" Schema summary saved to kg_artifacts/schema_summary.json")
    print(f"   (This will be used by the RAG pipeline in Step 5)")

if __name__ == "__main__":
    run_sparql_queries()