import torch
import json
import os
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from sklearn.manifold import TSNE
from pykeen.pipeline import pipeline
from pykeen.triples import TriplesFactory
from rdflib import Graph, Namespace, RDF

VG = Namespace("http://videogame-kg.org/ontology#")

def get_entity_types():
    """Load entity types from RDF graph."""
    g = Graph()
    g.parse("kg_artifacts/expanded.nt", format="nt")

    entity_types = {}
    for s, p, o in g.triples((None, RDF.type, None)):
        name = str(s).split("/")[-1]
        typ = str(o).split("#")[-1]
        if typ in ("Game", "Developer", "Publisher", "Platform", "Genre"):
            entity_types[name] = typ
    return entity_types

def run_tsne():
    os.makedirs("reports", exist_ok=True)

    # Retrain to get embeddings
    print(" Retraining DistMult to extract embeddings...")
    data_dir = "data/kge"
    train_tf = TriplesFactory.from_path(f"{data_dir}/train.txt")
    valid_tf = TriplesFactory.from_path(f"{data_dir}/valid.txt",
        entity_to_id=train_tf.entity_to_id,
        relation_to_id=train_tf.relation_to_id)
    test_tf = TriplesFactory.from_path(f"{data_dir}/test.txt",
        entity_to_id=train_tf.entity_to_id,
        relation_to_id=train_tf.relation_to_id)

    result = pipeline(
        training=train_tf,
        validation=valid_tf,
        testing=test_tf,
        model="DistMult",
        model_kwargs=dict(embedding_dim=64),
        training_kwargs=dict(num_epochs=100, batch_size=16),
        optimizer="Adam",
        optimizer_kwargs=dict(lr=0.01),
        random_seed=42,
    )

    # Extract embeddings
    model = result.model
    entity_embeddings = model.entity_representations[0]().detach().numpy()
    entity_to_id = train_tf.entity_to_id
    id_to_entity = {v: k for k, v in entity_to_id.items()}

    print(f" Got embeddings: {entity_embeddings.shape}")

    # Get entity types
    entity_types = get_entity_types()

    # Run t-SNE
    print(" Running t-SNE...")
    tsne = TSNE(n_components=2, random_state=42, perplexity=30, max_iter=1000)
    embeddings_2d = tsne.fit_transform(entity_embeddings)

    # Color map
    color_map = {
        "Game":      "#4C72B0",
        "Developer": "#DD8452",
        "Publisher": "#55A868",
        "Platform":  "#C44E52",
        "Genre":     "#8172B2",
        "Unknown":   "#aaaaaa",
    }

    # Build plot
    fig, ax = plt.subplots(figsize=(14, 10))
    fig.patch.set_facecolor("#f8f9fa")
    ax.set_facecolor("#f8f9fa")

    plotted_types = set()
    for idx in range(len(embeddings_2d)):
        entity_name = id_to_entity.get(idx, "")
        etype = entity_types.get(entity_name, "Unknown")
        color = color_map.get(etype, "#aaaaaa")
        plotted_types.add(etype)

        ax.scatter(
            embeddings_2d[idx, 0],
            embeddings_2d[idx, 1],
            c=color,
            alpha=0.75,
            s=40,
            edgecolors="white",
            linewidths=0.4,
        )

        # Label only well-known games
        known = ["Tetris", "Minecraft", "Overwatch", "Fortnite",
                 "Nintendo", "Capcom", "Electronic_Arts",
                 "Puzzle", "Action", "Role-playing"]
        if any(k in entity_name for k in known):
            ax.annotate(
                entity_name.replace("_", " ")[:20],
                (embeddings_2d[idx, 0], embeddings_2d[idx, 1]),
                fontsize=7, alpha=0.9,
                xytext=(4, 4), textcoords="offset points"
            )

    # Legend
    legend_handles = [
        mpatches.Patch(color=color_map[t], label=t)
        for t in ["Game", "Developer", "Publisher", "Platform", "Genre"]
        if t in plotted_types
    ]
    ax.legend(handles=legend_handles, loc="upper right",
              fontsize=10, framealpha=0.9, title="Entity Type")

    ax.set_title("t-SNE Visualization of DistMult KGE Embeddings\nVideo Game Knowledge Graph",
                 fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("t-SNE dimension 1", fontsize=11)
    ax.set_ylabel("t-SNE dimension 2", fontsize=11)
    ax.grid(True, alpha=0.3, linestyle="--")

    plt.tight_layout()
    output_path = "reports/tsne_embeddings.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f" t-SNE plot saved to {output_path}")
    plt.show()

if __name__ == "__main__":
    run_tsne()