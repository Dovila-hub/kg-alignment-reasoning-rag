import json
import ollama
from rdflib import Graph
import re
import os

g = Graph()
g.parse("kg_artifacts/expanded.ttl", format="turtle")

with open("kg_artifacts/schema_summary.json") as f:
    schema = json.load(f)

SCHEMA_PROMPT = """
You are a SPARQL expert for a Video Game Knowledge Graph.

Ontology namespace: http://videogame-kg.org/ontology#  (prefix: vg:)
Resource namespace: http://videogame-kg.org/resource/   (prefix: vgr:)

Classes: Game, Developer, Publisher, Platform, Genre

Properties:
- vg:hasTitle      (Game → string literal)
- vg:releaseYear   (Game → string literal, e.g. "2015")
- vg:salesMillions (Game → float)
- vg:hasDeveloper  (Game → Developer)
- vg:hasPublisher  (Game → Publisher)
- vg:hasPlatform   (Game → Platform)
- vg:hasGenre      (Game → Genre)
- rdfs:label       (Developer/Publisher/Platform/Genre → string)

IMPORTANT rules:
- Always use PREFIX declarations
- Use rdfs:label to get names of Developer, Publisher, Platform, Genre
- releaseYear is stored as a plain string literal like "2015"
- To filter by year use: FILTER(STR(?year) > "2010")
- salesMillions is a float, filter with: FILTER(?sales > 100)
- Always use LIMIT 20 unless asked for counts
- Return ONLY the SPARQL query, no explanation, no markdown, no backticks

Example:
Question: What games were developed by Nintendo?
PREFIX vg: <http://videogame-kg.org/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?title WHERE {
    ?game vg:hasTitle ?title .
    ?game vg:hasDeveloper ?dev .
    ?dev rdfs:label ?devLabel .
    FILTER(LCASE(STR(?devLabel)) = "nintendo")
}
LIMIT 20

Example:
Question: Which games sold more than 50 million copies?
PREFIX vg: <http://videogame-kg.org/ontology#>
SELECT ?title ?sales WHERE {
    ?game vg:hasTitle ?title .
    ?game vg:salesMillions ?sales .
    FILTER(?sales > 50)
}
ORDER BY DESC(?sales)
LIMIT 20
"""

def nl_to_sparql(question: str) -> str:
    response = ollama.chat(
        model="llama3.2",
        messages=[
            {"role": "system", "content": SCHEMA_PROMPT},
            {"role": "user", "content": f"Question: {question}"}
        ]
    )
    return response["message"]["content"].strip()

def clean_sparql(raw: str) -> str:
    raw = re.sub(r"```sparql|```", "", raw).strip()
    # Keep only from PREFIX or SELECT onwards
    for keyword in ["PREFIX", "SELECT", "ASK", "CONSTRUCT"]:
        idx = raw.find(keyword)
        if idx != -1:
            return raw[idx:]
    return raw

def execute_sparql(query: str):
    try:
        results = list(g.query(query))
        return results, None
    except Exception as e:
        return None, str(e)

def self_repair(question: str, bad_query: str, error: str) -> str:
    repair_prompt = f"""This SPARQL query failed:

{bad_query}

Error: {error}

Fix it for this question: {question}
Return ONLY the corrected SPARQL, no explanation, no backticks."""

    response = ollama.chat(
        model="llama3.2",
        messages=[
            {"role": "system", "content": SCHEMA_PROMPT},
            {"role": "user", "content": repair_prompt}
        ]
    )
    return response["message"]["content"].strip()

def format_results(results) -> str:
    if not results:
        return None
    lines = []
    for row in results[:10]:
        lines.append("  • " + " | ".join(str(v) for v in row))
    if len(results) > 10:
        lines.append(f"  ... and {len(results)-10} more")
    return "\n".join(lines)

def answer(question: str, verbose: bool = True) -> dict:
    if verbose:
        print(f"\n{'='*55}")
        print(f"Question: {question}")
        print(f"{'='*55}")

    raw_query = nl_to_sparql(question)
    query = clean_sparql(raw_query)

    if verbose:
        print(f"\n[Generated SPARQL]\n{query}")

    results, error = execute_sparql(query)

    repaired = False
    if error:
        if verbose:
            print(f"\n[Error] {error}")
            print("[Self-repair triggered...]")
        repaired_raw = self_repair(question, query, error)
        repaired_query = clean_sparql(repaired_raw)
        results, error = execute_sparql(repaired_query)
        query = repaired_query
        repaired = True
        if verbose:
            print(f"[Repaired SPARQL]\n{repaired_query}")

    formatted = format_results(results)

    if verbose:
        print(f"\n[Answer]")
        if formatted:
            print(formatted)
        elif results is not None and len(results) == 0:
            print("  No matching data found in the knowledge graph.")
            print("  (The query ran correctly but this entity may not be in our 135-game dataset)")
        else:
            print("  Query could not be executed.")

    return {
        "question": question,
        "sparql": query,
        "results": formatted or "No data found",
        "repaired": repaired,
    }

EVAL_QUESTIONS = [
    "Which games were published by Nintendo?",
    "Which games have sold more than 100 million copies?",
    "What games were self-published by their developer?",
    "Which games were released after 2010?",
    "How many games does each publisher have?",
]

BASELINE_ANSWERS = [
    "Unknown — no system available",
    "Unknown — no system available",
    "Unknown — no system available",
    "Unknown — no system available",
    "Unknown — no system available",
]

def run_evaluation():
    print("\n" + "="*55)
    print("RAG EVALUATION — Baseline vs RAG")
    print("="*55)

    eval_results = []
    for i, question in enumerate(EVAL_QUESTIONS):
        result = answer(question, verbose=False)
        eval_results.append({
            "question": question,
            "baseline": BASELINE_ANSWERS[i],
            "rag_answer": result["results"],
            "sparql": result["sparql"],
            "repaired": result["repaired"],
        })
        short = result["results"][:120]
        print(f"\nQ{i+1}: {question}")
        print(f"  Baseline : {BASELINE_ANSWERS[i]}")
        print(f"  RAG      : {short}{'...' if len(result['results'])>120 else ''}")
        print(f"  Repaired : {result['repaired']}")

    os.makedirs("data/samples", exist_ok=True)
    with open("data/samples/rag_evaluation.json", "w") as f:
        json.dump(eval_results, f, indent=2)
    print(f"\n Evaluation saved to data/samples/rag_evaluation.json")

if __name__ == "__main__":
    print(" Video Game KG — RAG Demo")
    print("Commands: 'eval' to run evaluation, 'quit' to exit\n")

    while True:
        try:
            q = input("Your question: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break
        elif q.lower() == "eval":
            run_evaluation()
        elif q:
            answer(q)