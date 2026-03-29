import json
import os
import random
from rdflib import Graph, Namespace, RDF

VG = Namespace("http://videogame-kg.org/ontology#")

def uri_to_name(uri):
    return str(uri).split("/")[-1]

def prepare(input_nt="kg_artifacts/expanded.nt",
            output_dir="data/kge"):

    os.makedirs(output_dir, exist_ok=True)

    g = Graph()
    g.parse(input_nt, format="nt")

    # Extract all meaningful triples (skip rdf:type and ontology triples)
    skip_predicates = {
        "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
        "http://www.w3.org/2000/01/rdf-schema#label",
        "http://www.w3.org/2002/07/owl#inverseOf",
        "http://www.w3.org/2000/01/rdf-schema#domain",
        "http://www.w3.org/2000/01/rdf-schema#range",
    }

    triples = []
    for s, p, o in g:
        p_str = str(p)
        s_str = str(s)
        o_str = str(o)

        if p_str in skip_predicates:
            continue
        if "ontology#" in s_str:  # skip ontology definitions
            continue
        if o_str.startswith("http://www.w3.org"):
            continue

        # Convert to short names
        s_name = uri_to_name(s_str)
        p_name = uri_to_name(p_str)
        o_name = uri_to_name(o_str) if o_str.startswith("http") else o_str

        if s_name and p_name and o_name:
            triples.append((s_name, p_name, o_name))

    # Remove duplicates
    triples = list(set(triples))
    random.seed(42)
    random.shuffle(triples)

    total = len(triples)
    train_end = int(total * 0.7)
    valid_end = int(total * 0.85)

    train = triples[:train_end]
    valid = triples[train_end:valid_end]
    test  = triples[valid_end:]

    def save(split, path):
        with open(path, "w", encoding="utf-8") as f:
            for s, p, o in split:
                f.write(f"{s}\t{p}\t{o}\n")

    save(train, f"{output_dir}/train.txt")
    save(valid, f"{output_dir}/valid.txt")
    save(test,  f"{output_dir}/test.txt")

    print(f" Dataset prepared from {total} triples")
    print(f"   Train : {len(train)}")
    print(f"   Valid : {len(valid)}")
    print(f"   Test  : {len(test)}")
    print(f"   Saved to {output_dir}/")

if __name__ == "__main__":
    prepare()