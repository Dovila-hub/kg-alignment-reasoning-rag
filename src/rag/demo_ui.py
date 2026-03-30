import json
import ollama
from rdflib import Graph
from http.server import HTTPServer, BaseHTTPRequestHandler
import re
import urllib.parse

g = Graph()
g.parse("kg_artifacts/expanded.ttl", format="turtle")

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
"""

def nl_to_sparql(question):
    response = ollama.chat(
        model="llama3.2",
        messages=[
            {"role": "system", "content": SCHEMA_PROMPT},
            {"role": "user", "content": f"Question: {question}"}
        ]
    )
    return response["message"]["content"].strip()

def clean_sparql(raw):
    raw = re.sub(r"```sparql|```", "", raw).strip()
    for keyword in ["PREFIX", "SELECT", "ASK", "CONSTRUCT"]:
        idx = raw.find(keyword)
        if idx != -1:
            return raw[idx:]
    return raw

def execute_sparql(query):
    try:
        results = list(g.query(query))
        return results, None
    except Exception as e:
        return None, str(e)

def self_repair(question, bad_query, error):
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

def process_question(question):
    raw = nl_to_sparql(question)
    query = clean_sparql(raw)
    results, error = execute_sparql(query)
    repaired = False

    if error:
        repaired_raw = self_repair(question, query, error)
        query = clean_sparql(repaired_raw)
        results, error = execute_sparql(query)
        repaired = True

    rows = []
    if results:
        for row in results[:15]:
            rows.append([str(v) for v in row])

    return {
        "query": query,
        "rows": rows,
        "repaired": repaired,
        "error": str(error) if error else None,
        "count": len(results) if results else 0
    }

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Video Game KG — RAG Demo</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #0f0f1a; color: #e0e0e0; min-height: 100vh; }
  header { background: linear-gradient(135deg, #1a1a2e, #16213e);
           padding: 2rem; text-align: center; border-bottom: 1px solid #2a2a4a; }
  header h1 { font-size: 1.8rem; color: #7c83ff; margin-bottom: 0.4rem; }
  header p { color: #888; font-size: 0.9rem; }
  .container { max-width: 900px; margin: 2rem auto; padding: 0 1.5rem; }
  .search-box { display: flex; gap: 0.75rem; margin-bottom: 1.5rem; }
  input[type=text] {
    flex: 1; padding: 0.85rem 1.2rem; border-radius: 10px;
    border: 1px solid #2a2a4a; background: #1a1a2e;
    color: #e0e0e0; font-size: 1rem; outline: none;
    transition: border 0.2s;
  }
  input[type=text]:focus { border-color: #7c83ff; }
  button {
    padding: 0.85rem 1.8rem; border-radius: 10px; border: none;
    background: #7c83ff; color: white; font-size: 1rem;
    cursor: pointer; transition: background 0.2s; white-space: nowrap;
  }
  button:hover { background: #5a62e0; }
  button:disabled { background: #444; cursor: not-allowed; }
  .suggestions { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 2rem; }
  .chip {
    padding: 0.4rem 0.9rem; border-radius: 20px; font-size: 0.82rem;
    background: #1a1a2e; border: 1px solid #2a2a4a; color: #aaa;
    cursor: pointer; transition: all 0.2s;
  }
  .chip:hover { border-color: #7c83ff; color: #7c83ff; }
  .card {
    background: #1a1a2e; border: 1px solid #2a2a4a;
    border-radius: 12px; padding: 1.5rem; margin-bottom: 1.2rem;
  }
  .card-title { font-size: 0.75rem; text-transform: uppercase;
                letter-spacing: 0.08em; color: #7c83ff; margin-bottom: 0.75rem; }
  .sparql { background: #0d0d1a; border-radius: 8px; padding: 1rem;
            font-family: 'Courier New', monospace; font-size: 0.82rem;
            color: #a8d8a8; white-space: pre-wrap; overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; }
  th { text-align: left; padding: 0.6rem 0.8rem; font-size: 0.8rem;
       color: #7c83ff; border-bottom: 1px solid #2a2a4a; }
  td { padding: 0.6rem 0.8rem; font-size: 0.88rem;
       border-bottom: 1px solid #1a1a2e; color: #ccc; }
  tr:hover td { background: #12122a; }
  .badge { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 6px;
           font-size: 0.75rem; margin-left: 0.5rem; }
  .badge-repair { background: #2a1a0a; color: #f0a500; border: 1px solid #f0a500; }
  .badge-ok { background: #0a2a1a; color: #4caf50; border: 1px solid #4caf50; }
  .badge-error { background: #2a0a0a; color: #f44336; border: 1px solid #f44336; }
  .stats { display: flex; gap: 1rem; margin-bottom: 1rem; }
  .stat { background: #12122a; border-radius: 8px; padding: 0.6rem 1rem;
          font-size: 0.82rem; color: #888; }
  .stat span { color: #7c83ff; font-weight: 600; }
  .loading { text-align: center; padding: 2rem; color: #666; }
  .spinner { display: inline-block; width: 20px; height: 20px;
             border: 2px solid #333; border-top-color: #7c83ff;
             border-radius: 50%; animation: spin 0.8s linear infinite;
             margin-right: 0.5rem; vertical-align: middle; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .empty { text-align: center; padding: 3rem; color: #444; }
  .empty p { font-size: 1.5rem; margin-bottom: 0.5rem; }
  footer { text-align: center; padding: 2rem; color: #444; font-size: 0.8rem; }
</style>
</head>
<body>
<header>
  <h1> Video Game Knowledge Graph</h1>
  <p>RAG Demo — Natural Language → SPARQL → Results &nbsp;·&nbsp; Master 1 Web Data Mining & Semantics</p>
</header>
<div class="container">
  <div class="search-box">
    <input type="text" id="question" placeholder="Ask anything about video games..."
           onkeydown="if(event.key==='Enter') ask()">
    <button onclick="ask()" id="btn">Ask</button>
  </div>
  <div class="suggestions">
    <span class="chip" onclick="fill('Which games were published by Nintendo?')">Nintendo games</span>
    <span class="chip" onclick="fill('Which games sold more than 100 million copies?')">Top sellers</span>
    <span class="chip" onclick="fill('What games were self-published by their developer?')">Self-published</span>
    <span class="chip" onclick="fill('Which games were released after 2010?')">After 2010</span>
    <span class="chip" onclick="fill('How many games does each publisher have?')">Publisher stats</span>
    <span class="chip" onclick="fill('What genre is Tetris?')">Tetris genre</span>
  </div>
  <div id="result">
    <div class="empty">
      <p>🕹️</p>
      <div style="color:#555">Ask a question about the video game knowledge graph</div>
    </div>
  </div>
</div>
<footer>Dovila Longmis · Master 1 Web Data Mining & Semantics · 2026</footer>
<script>
function fill(q) {
  document.getElementById('question').value = q;
  ask();
}

async function ask() {
  const q = document.getElementById('question').value.trim();
  if (!q) return;

  document.getElementById('btn').disabled = true;
  document.getElementById('result').innerHTML =
    '<div class="loading"><span class="spinner"></span>Generating SPARQL and querying the graph...</div>';

  try {
    const res = await fetch('/ask?q=' + encodeURIComponent(q));
    const data = await res.json();

    const badge = data.repaired
      ? '<span class="badge badge-repair">⚡ self-repaired</span>'
      : '<span class="badge badge-ok">✓ direct</span>';

    const errorBadge = data.error
      ? '<span class="badge badge-error">error</span>' : '';

    let tableHtml = '';
    if (data.rows && data.rows.length > 0) {
      tableHtml = '<table><tr>' +
        data.rows[0].map((_, i) => `<th>Column ${i+1}</th>`).join('') +
        '</tr>';
      data.rows.forEach(row => {
        tableHtml += '<tr>' + row.map(v =>
          `<td>${v.length > 60 ? v.substring(0,60)+'...' : v}</td>`
        ).join('') + '</tr>';
      });
      tableHtml += '</table>';
    } else {
      tableHtml = '<div style="color:#666;padding:1rem">No results found in the knowledge graph.</div>';
    }

    document.getElementById('result').innerHTML = `
      <div class="stats">
        <div class="stat">Results: <span>${data.count}</span></div>
        <div class="stat">Status: <span>${data.repaired ? 'Self-repaired' : 'OK'}</span></div>
      </div>
      <div class="card">
        <div class="card-title">Generated SPARQL ${badge} ${errorBadge}</div>
        <div class="sparql">${data.query.replace(/</g,'&lt;').replace(/>/g,'&gt;')}</div>
      </div>
      <div class="card">
        <div class="card-title">Results (${data.count} found, showing up to 15)</div>
        ${tableHtml}
      </div>
    `;
  } catch(e) {
    document.getElementById('result').innerHTML =
      '<div class="card" style="border-color:#f44336">Error: ' + e.message + '</div>';
  }
  document.getElementById('btn').disabled = false;
}
</script>
</body>
</html>"""

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress request logs

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(HTML.encode())

        elif self.path.startswith("/ask"):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            question = params.get("q", [""])[0]

            result = process_question(question)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())

        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    port = 8080
    print(f" Video Game KG Demo UI")
    print(f"   Open http://localhost:{port} in your browser")
    print(f"   Press Ctrl+C to stop\n")
    HTTPServer(("", port), Handler).serve_forever()