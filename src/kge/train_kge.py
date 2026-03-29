import torch
from pykeen.pipeline import pipeline
from pykeen.triples import TriplesFactory
import json
import os

def run(model_name, train_tf, valid_tf, test_tf, epochs=100):
    print(f"\n{'='*50}")
    print(f"Training {model_name}...")
    print(f"{'='*50}")

    result = pipeline(
        training=train_tf,
        validation=valid_tf,
        testing=test_tf,
        model=model_name,
        model_kwargs=dict(embedding_dim=64),
        training_kwargs=dict(num_epochs=epochs, batch_size=16),
        optimizer="Adam",
        optimizer_kwargs=dict(lr=0.01),
        evaluator_kwargs=dict(filtered=True),
        random_seed=42,
    )

    # Navigate the correct nested structure:
    both_realistic = result.metric_results.to_dict()["both"]["realistic"]

    mrr = both_realistic.get("inverse_harmonic_mean_rank", 0.0)
    h1  = both_realistic.get("hits_at_1",  0.0)
    h3  = both_realistic.get("hits_at_3",  0.0)
    h10 = both_realistic.get("hits_at_10", 0.0)

    print(f"\n📊 {model_name} Results:")
    print(f"   MRR      : {mrr:.4f}")
    print(f"   Hits@1   : {h1:.4f}")
    print(f"   Hits@3   : {h3:.4f}")
    print(f"   Hits@10  : {h10:.4f}")

    return {
        "model": model_name,
        "MRR":    round(mrr, 4),
        "Hits@1": round(h1,  4),
        "Hits@3": round(h3,  4),
        "Hits@10":round(h10, 4),
    }

def main():
    data_dir = "data/kge"
    os.makedirs(data_dir, exist_ok=True)

    train_tf = TriplesFactory.from_path(f"{data_dir}/train.txt")
    valid_tf = TriplesFactory.from_path(
        f"{data_dir}/valid.txt",
        entity_to_id=train_tf.entity_to_id,
        relation_to_id=train_tf.relation_to_id,
    )
    test_tf = TriplesFactory.from_path(
        f"{data_dir}/test.txt",
        entity_to_id=train_tf.entity_to_id,
        relation_to_id=train_tf.relation_to_id,
    )

    print(f" Dataset loaded:")
    print(f"   Entities  : {train_tf.num_entities}")
    print(f"   Relations : {train_tf.num_relations}")
    print(f"   Train triples: {train_tf.num_triples}")
    print(f"   Valid triples: {valid_tf.num_triples}")
    print(f"   Test  triples: {test_tf.num_triples}")

    all_results = []
    for model in ["TransE", "DistMult","RotatE","ComplEx"]:
        r = run(model, train_tf, valid_tf, test_tf, epochs=100)
        all_results.append(r)

    with open(f"{data_dir}/kge_results.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n Results saved to {data_dir}/kge_results.json")
    print(f"\n Final Comparison:")
    print(f"{'Model':<12} {'MRR':<8} {'H@1':<8} {'H@3':<8} {'H@10':<8}")
    print("-" * 44)
    for r in all_results:
        print(f"{r['model']:<12} {r['MRR']:<8} {r['Hits@1']:<8} {r['Hits@3']:<8} {r['Hits@10']:<8}")

if __name__ == "__main__":
    main()