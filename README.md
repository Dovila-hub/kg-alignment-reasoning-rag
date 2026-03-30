
# Knowledge Graph Construction · Alignment · Reasoning & KGE · RAG

**Project done by Alida Dovila Zogo Kanda Longmis — Master 1, Web Data Mining and Semantics**

---

## About this project

Honestly, when I first looked at the project requirements, it felt overwhelming. Four lab sessions worth of content combined into one full pipeline which was crawling, knowledge graphs, reasoning, embeddings, and a RAG system all from scratch. I didn't know where to start.

But I figured it out step by step. The idea was to build a complete knowledge graph pipeline around a domain of my choice. I went with **video games** because i do love it and  it's a domain with rich, structured data and clear relationships between entities like games, developers, publishers, platforms and genres.

The data comes from Wikipedia's lists of best-selling and best-rated video games. From there, I built everything: a crawler that scrapes and cleans the data, a Named Entity Recognition pipeline, an RDF knowledge graph with a proper OWL ontology, Wikidata alignment, SWRL reasoning rules, knowledge graph embeddings trained with two different models, and finally a RAG system that lets you ask natural language questions and get answers directly from the graph.

One of the trickier parts was getting the SWRL reasoner to work — it needs Java installed, which took some figuring out. The RAG pipeline was also challenging because getting the LLM to generate valid SPARQL consistently required careful prompt engineering and a self-repair mechanism for when queries fail.

Overall this project taught me a lot about how all these pieces fit together in a real semantic web pipeline.

---

## Installation
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

You also need:
- **Java 21+** for the HermiT reasoner: `brew install openjdk`
- **Ollama** with llama3.2 for the RAG demo: `brew install ollama && ollama pull llama3.2`

---

## How to run each module
```bash
# 1. Crawl Wikipedia
python src/crawl/crawler.py

# 2. Clean data
python src/ie/clean.py

# 3. NER
python src/ie/ner.py

# 4. Build RDF graph
python src/kg/build_graph.py

# 5. Align to Wikidata
python src/kg/align.py

# 6. SPARQL expansion
python src/kg/sparql_expand.py

# 7. SWRL reasoning
python src/reason/swrl_rules.py

# 8. KGE training
python src/kge/prepare_data.py
python src/kge/train_kge.py

# 9. RAG demo
python src/rag/rag_pipeline.py
```

---

## How to run the RAG demo

First start Ollama in a separate terminal:
```bash
ollama serve
```

Then in your main terminal:
```bash
python src/rag/rag_pipeline.py
```

Type any question about video games, for example:
- `Which games were published by Nintendo?`
- `Which games sold more than 100 million copies?`
- `What games were self-published by their developer?`

Type `eval` to run the full evaluation (baseline vs RAG).
Type `quit` to exit.

---

## Hardware requirements

- macOS with Apple Silicon (tested on M3)
- 8GB RAM minimum
- ~15GB disk space for the Ollama model
- Java 21+ for the HermiT reasoner
- Ollama with llama3.2

---

## KB Statistics

| Metric | Value |
|--------|-------|
| Games | 135 |
| Developers | 86 |
| Publishers | 44 |
| Platforms | 26 |
| Genres | 59 |
| Total RDF triples | 1,235 |
| Wikidata alignments | 14 |

---

## Project structure
```
kg-alignment-reasoning-rag/
├── src/
│   ├── crawl/       # Wikipedia crawler
│   ├── ie/          # Cleaning + NER
│   ├── kg/          # RDF graph, SPARQL, Wikidata alignment
│   ├── reason/      # SWRL rules with HermiT reasoner
│   ├── kge/         # KGE training: TransE and DistMult
│   └── rag/         # RAG pipeline: NL→SPARQL + self-repair
├── data/
│   ├── raw/         # Raw crawled data (740 entries)
│   ├── samples/     # Cleaned, NER-annotated, evaluation data
│   └── kge/         # train/valid/test triple splits
├── kg_artifacts/    # Ontology, RDF graph, alignment, schema summary

├── requirements.txt
└── README.md
```
