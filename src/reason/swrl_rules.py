from owlready2 import *
import os

# ─────────────────────────────────────────
# PART 1 — family.owl: grandparent rule
# ─────────────────────────────────────────

def run_family_rules():
    print("=" * 50)
    print("PART 1 — family.owl SWRL Rules")
    print("=" * 50)

    # Load with absolute path
    path = os.path.abspath("kg_artifacts/family.owl")
    onto = get_ontology(f"file://{path}").load()

    fam = onto.get_namespace("http://family.owl#")

    with onto:
        # Define properties if not already present
        if not onto.search_one(iri="http://family.owl#hasGrandparent"):
            class hasGrandparent(onto.search_one(iri="http://family.owl#Person") >> onto.search_one(iri="http://family.owl#Person")):
                namespace = fam

        if not onto.search_one(iri="http://family.owl#hasSibling"):
            class hasSibling(onto.search_one(iri="http://family.owl#Person") >> onto.search_one(iri="http://family.owl#Person")):
                namespace = fam

        # SWRL Rule 1: grandparent
        rule1 = Imp()
        rule1.set_as_rule(
            "hasParent(?x, ?y), hasParent(?y, ?z) -> hasGrandparent(?x, ?z)",
            namespaces=[fam]
        )

        # SWRL Rule 2: sibling
        rule2 = Imp()
        rule2.set_as_rule(
            "hasParent(?x, ?p), hasParent(?y, ?p), differentFrom(?x, ?y) -> hasSibling(?x, ?y)",
            namespaces=[fam]
        )

    print("\n🔍 Running reasoner...")
    with onto:
        sync_reasoner(infer_property_values=True)

    print("\n Inferred grandparent relationships:")
    Person = onto.search_one(iri="http://family.owl#Person")
    hasGrandparent_prop = onto.search_one(iri="http://family.owl#hasGrandparent")
    hasSibling_prop = onto.search_one(iri="http://family.owl#hasSibling")

    found_gp = False
    found_sib = False

    for person in onto.individuals():
        if hasGrandparent_prop:
            gps = hasGrandparent_prop[person]
            for gp in gps:
                print(f"  {person.name} hasGrandparent {gp.name}")
                found_gp = True

    if not found_gp:
        # Fallback: manually chain hasParent
        hasParent_prop = onto.search_one(iri="http://family.owl#hasParent")
        print("  (reasoner didn't fire — showing manual chaining)")
        for person in onto.individuals():
            parents = hasParent_prop[person] if hasParent_prop else []
            for parent in parents:
                grandparents = hasParent_prop[parent] if hasParent_prop else []
                for gp in grandparents:
                    print(f"  {person.name} hasGrandparent {gp.name}")

    print("\n👫 Inferred sibling relationships:")
    for person in onto.individuals():
        if hasSibling_prop:
            sibs = hasSibling_prop[person]
            for sib in sibs:
                print(f"  {person.name} hasSibling {sib.name}")
                found_sib = True

    if not found_sib:
        hasParent_prop = onto.search_one(iri="http://family.owl#hasParent")
        print("  (showing manual chaining)")
        for person in onto.individuals():
            parents = hasParent_prop[person] if hasParent_prop else []
            for parent in parents:
                for other in onto.individuals():
                    if other != person and parent in (hasParent_prop[other] or []):
                        print(f"  {person.name} hasSibling {other.name}")


# ─────────────────────────────────────────
# PART 2 — Video Game KB: self-published rule
# ─────────────────────────────────────────

def run_videogame_rules():
    print("\n" + "=" * 50)
    print("PART 2 — Video Game KB SWRL Rules")
    print("=" * 50)

    from rdflib import Graph, Namespace

    VG = Namespace("http://videogame-kg.org/ontology#")
    VGR = Namespace("http://videogame-kg.org/resource/")

    rdf_g = Graph()
    rdf_g.parse("kg_artifacts/expanded.ttl", format="turtle")

    print("\n SWRL Rule:")
    print("  Game(?g) ∧ hasDeveloper(?g, ?x) ∧ hasPublisher(?g, ?x)")
    print("  → SelfPublishedGame(?g)")
    print("\n  Meaning: if the same entity develops AND publishes a game,")
    print("  it is classified as a SelfPublishedGame.\n")

    # Check by identical URI
    query1 = """
    PREFIX vg: <http://videogame-kg.org/ontology#>
    SELECT ?title ?org WHERE {
        ?game vg:hasDeveloper ?org .
        ?game vg:hasPublisher ?org .
        ?game vg:hasTitle ?title .
    }
    """
    results1 = list(rdf_g.query(query1))
    print(f" Self-published games (same URI for dev & pub):")
    if results1:
        for row in results1:
            print(f"   {row.title}  →  {str(row.org).split('/')[-1]}")
    else:
        print("  (none — dev and pub always have separate URIs in this dataset)")

    # Check by matching label
    query2 = """
    PREFIX vg: <http://videogame-kg.org/ontology#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?title ?devLabel WHERE {
        ?game vg:hasTitle ?title .
        ?game vg:hasDeveloper ?dev .
        ?game vg:hasPublisher ?pub .
        ?dev rdfs:label ?devLabel .
        ?pub rdfs:label ?pubLabel .
        FILTER(LCASE(STR(?devLabel)) = LCASE(STR(?pubLabel)))
    }
    """
    results2 = list(rdf_g.query(query2))
    print(f"\n Self-published games (dev label = pub label):")
    if results2:
        for row in results2:
            print(f"  {row.title}  →  {row.devLabel}")
    else:
        print("  (none found in current dataset)")
        print("\n   Example that WOULD fire this rule:")
        print("     Minecraft → developer: Mojang, publisher: Mojang")
        print("     → classified as SelfPublishedGame ")


if __name__ == "__main__":
    run_family_rules()
    run_videogame_rules()