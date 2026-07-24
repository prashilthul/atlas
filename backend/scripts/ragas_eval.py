"""
RAGAS batch evaluation script for Paper Pilot.

Standalone script (not in pyproject.toml).
Install dependencies:
    uv add ragas
    uv add datasets  (usually pulled by ragas)

Usage:
    uv run python scripts/ragas_eval.py
    uv run python scripts/ragas_eval.py --compare
"""

import argparse
import csv
import os
import sys

try:
    from datasets import Dataset
except ImportError:
    print("datasets not installed. Run: uv add datasets")
    sys.exit(1)

try:
    from ragas import evaluate
    from ragas.metrics import (
        answer_relevancy,
        context_precision,
        context_recall,
        faithfulness,
    )
except ImportError:
    print("ragas not installed. Run: uv add ragas")
    sys.exit(1)

_EXCERPTS = {
    "abstract": (
        "The dominant sequence transduction models are based on complex recurrent "
        "or convolutional neural networks that include an encoder and a decoder. "
        "The best performing models also connect the encoder and decoder through "
        "an attention mechanism. We propose a new simple network architecture, "
        "the Transformer, based solely on attention mechanisms, dispensing with "
        "recurrence and convolutions entirely."
    ),
    "intro": (
        "Recurrent neural networks, long short-term memory and gated recurrent "
        "neural networks in particular, have been firmly established as state of "
        "the art approaches in sequence modeling and transduction problems like "
        "language modeling and machine translation."
    ),
    "attention_def": (
        "An attention function can be described as mapping a query and a set of "
        "key-value pairs to an output, where the query, keys, values, and output "
        "are all vectors. The output is computed as a weighted sum of the values, "
        "where the weight assigned to each value is computed by a compatibility "
        "function of the query with the corresponding key."
    ),
    "scaled_dot_product": (
        "We call our particular attention 'Scaled Dot-Product Attention'. The "
        "input consists of queries and keys of dimension d_k, and values of "
        "dimension d_v. We compute the dot products of the query with all keys, "
        "divide each by sqrt(d_k), and apply a softmax function to obtain the "
        "weights on the values."
    ),
    "multi_head": (
        "Instead of performing a single attention function with d_model-dimensional "
        "keys, values, and queries, we found it beneficial to linearly project "
        "the queries, keys and values h times with different, learned linear "
        "projections to d_k, d_v and d_k dimensions, respectively."
    ),
    "positional_encoding": (
        "Since our model contains no recurrence and no convolution, in order for "
        "the model to make use of the order of the sequence, we must inject some "
        "information about the relative or absolute position of the tokens in "
        "the sequence."
    ),
    "results": (
        "The Transformer achieves 28.4 BLEU on the WMT 2014 English-to-German "
        "translation task, improving over the existing best results, including "
        "ensembles, by over 2 BLEU."
    ),
}


def load_dataset() -> list[dict]:
    """Return list of {question, answer, ground_truth, contexts}."""
    return [
        # --- Directly answerable from paper (10 cases) ---
        {
            "question": "What architecture is the Transformer based on?",
            "answer": "The Transformer is based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.",
            "ground_truth": "The Transformer is based solely on attention mechanisms, without recurrence or convolutions.",
            "contexts": [_EXCERPTS["abstract"]],
        },
        {
            "question": "What BLEU score does the Transformer achieve on WMT 2014 English-to-German?",
            "answer": "The Transformer achieves 28.4 BLEU on the WMT 2014 English-to-German translation task.",
            "ground_truth": "28.4 BLEU on WMT 2014 English-to-German.",
            "contexts": [_EXCERPTS["results"]],
        },
        {
            "question": "What is Scaled Dot-Product Attention?",
            "answer": "Scaled Dot-Product Attention takes queries and keys of dimension d_k and values of dimension d_v, computes dot products of the query with all keys, divides by sqrt(d_k), and applies softmax to obtain weights on the values.",
            "ground_truth": "An attention mechanism where the input consists of queries and keys of dimension d_k, and values of dimension d_v, computing dot products divided by sqrt(d_k) with a softmax.",
            "contexts": [_EXCERPTS["scaled_dot_product"]],
        },
        {
            "question": "Why does the Transformer need positional encoding?",
            "answer": "The Transformer needs positional encoding because it contains no recurrence and no convolution, so it must inject information about the relative or absolute position of tokens in the sequence.",
            "ground_truth": "Because the model has no recurrence or convolution, positional information must be injected separately.",
            "contexts": [_EXCERPTS["positional_encoding"]],
        },
        {
            "question": "What are the dominant sequence transduction models?",
            "answer": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder.",
            "ground_truth": "Complex recurrent or convolutional neural networks with an encoder and decoder.",
            "contexts": [_EXCERPTS["abstract"]],
        },
        {
            "question": "What is Multi-Head Attention?",
            "answer": "Multi-Head Attention linearly projects the queries, keys and values h times with different learned linear projections to d_k, d_v and d_k dimensions respectively, instead of performing a single attention function.",
            "ground_truth": "Multiple parallel attention heads created by linearly projecting queries, keys, and values h times with different learned projections.",
            "contexts": [_EXCERPTS["multi_head"]],
        },
        {
            "question": "What are the inputs to Scaled Dot-Product Attention?",
            "answer": "The inputs consist of queries and keys of dimension d_k, and values of dimension d_v.",
            "ground_truth": "Queries and keys of dimension d_k, and values of dimension d_v.",
            "contexts": [_EXCERPTS["scaled_dot_product"]],
        },
        {
            "question": "How much does the Transformer improve over existing models on WMT 2014?",
            "answer": "The Transformer improves over the existing best results, including ensembles, by over 2 BLEU on the WMT 2014 English-to-German translation task.",
            "ground_truth": "It improves by over 2 BLEU over existing best results including ensembles.",
            "contexts": [_EXCERPTS["results"]],
        },
        {
            "question": "What is an attention function?",
            "answer": "An attention function maps a query and a set of key-value pairs to an output, where the query, keys, values, and output are all vectors. The output is a weighted sum of the values.",
            "ground_truth": "A function that maps a query and key-value pairs to a vector output computed as a weighted sum of the values.",
            "contexts": [_EXCERPTS["attention_def"]],
        },
        {
            "question": "What networks are state of the art for sequence modeling?",
            "answer": "Recurrent neural networks, long short-term memory and gated recurrent neural networks have been established as state of the art for sequence modeling and transduction problems.",
            "ground_truth": "RNNs, LSTM, and GRU are state of the art for sequence modeling and transduction.",
            "contexts": [_EXCERPTS["intro"]],
        },
        # --- Synthesis across sections (5 cases) ---
        {
            "question": "How does the Transformer avoid sequential computation?",
            "answer": "The Transformer avoids sequential computation by using attention mechanisms instead of recurrence. It processes all tokens in parallel through self-attention, dispensing with the sequential nature of RNNs entirely.",
            "ground_truth": "By using attention mechanisms instead of recurrence, allowing parallel processing of all tokens.",
            "contexts": [_EXCERPTS["abstract"], _EXCERPTS["positional_encoding"]],
        },
        {
            "question": "Explain the components of the Transformer's attention mechanism.",
            "answer": "The Transformer uses Scaled Dot-Product Attention and Multi-Head Attention. Scaled Dot-Product Attention computes weighted sums via dot products scaled by sqrt(d_k). Multi-Head Attention runs multiple attention functions in parallel with different linear projections.",
            "ground_truth": "Scaled Dot-Product Attention for computing attention weights and Multi-Head Attention for parallel attention functions.",
            "contexts": [_EXCERPTS["scaled_dot_product"], _EXCERPTS["multi_head"]],
        },
        {
            "question": "Why is the Transformer considered simpler than previous models?",
            "answer": "The Transformer is simpler because it dispenses with recurrence and convolutions entirely, relying solely on attention mechanisms. Previous models required complex RNN or CNN architectures.",
            "ground_truth": "It dispenses with recurrence and convolutions, using only attention mechanisms.",
            "contexts": [_EXCERPTS["abstract"]],
        },
        {
            "question": "How does the Transformer handle token position?",
            "answer": "Since the Transformer has no recurrence or convolution, it injects information about the relative or absolute position of tokens in the sequence through positional encoding.",
            "ground_truth": "Through positional encoding that injects relative or absolute position information.",
            "contexts": [_EXCERPTS["positional_encoding"]],
        },
        {
            "question": "What makes the Transformer architecture novel?",
            "answer": "The Transformer is novel because it is based solely on attention mechanisms, completely dispensing with recurrence and convolutions that were the foundation of previous sequence transduction models.",
            "ground_truth": "Its use of only attention mechanisms without recurrence or convolutions.",
            "contexts": [_EXCERPTS["abstract"], _EXCERPTS["intro"]],
        },
        # --- Unrelated topics (5 cases) ---
        {
            "question": "What is backpropagation?",
            "answer": "The provided excerpts discuss the Transformer architecture for sequence transduction but do not cover backpropagation. Based solely on the given excerpts, I cannot provide information about backpropagation.",
            "ground_truth": "The provided excerpts do not discuss backpropagation.",
            "contexts": [_EXCERPTS["abstract"]],
        },
        {
            "question": "How does gradient descent work?",
            "answer": "The provided excerpts focus on the Transformer architecture and attention mechanisms but do not cover gradient descent. Based solely on the given excerpts, I cannot provide information about gradient descent.",
            "ground_truth": "The provided excerpts do not discuss gradient descent.",
            "contexts": [_EXCERPTS["intro"]],
        },
        {
            "question": "What is the difference between CNN and RNN?",
            "answer": "The provided excerpts mention that both convolutional and recurrent neural networks are used in sequence transduction models, but do not explain the differences between them. Based solely on the given excerpts, I cannot detail the differences.",
            "ground_truth": "The excerpts do not detail the differences between CNN and RNN.",
            "contexts": [_EXCERPTS["abstract"]],
        },
        {
            "question": "Explain transfer learning.",
            "answer": "The provided excerpts discuss sequence transduction models and the Transformer architecture but do not cover transfer learning. Based solely on the given excerpts, I cannot provide information about transfer learning.",
            "ground_truth": "The provided excerpts do not discuss transfer learning.",
            "contexts": [_EXCERPTS["intro"]],
        },
        {
            "question": "What is batch normalization?",
            "answer": "The provided excerpts discuss the Transformer architecture and attention mechanisms but do not cover batch normalization. Based solely on the given excerpts, I cannot provide information about batch normalization.",
            "ground_truth": "The provided excerpts do not discuss batch normalization.",
            "contexts": [_EXCERPTS["abstract"]],
        },
        # --- Citation requirements (3 cases) ---
        {
            "question": "What specific BLEU score does the Transformer achieve and on which task?",
            "answer": "The Transformer achieves 28.4 BLEU on the WMT 2014 English-to-German translation task, improving over existing best results by over 2 BLEU.",
            "ground_truth": "28.4 BLEU on WMT 2014 English-to-German, improving by over 2 BLEU.",
            "contexts": [_EXCERPTS["results"]],
        },
        {
            "question": "What is the key innovation of the Transformer architecture?",
            "answer": "The key innovation is that the Transformer is based solely on attention mechanisms, completely eliminating recurrence and convolutions from the architecture.",
            "ground_truth": "Being based solely on attention mechanisms without recurrence or convolutions.",
            "contexts": [_EXCERPTS["abstract"]],
        },
        {
            "question": "How does Multi-Head Attention project its inputs?",
            "answer": "Multi-Head Attention linearly projects the queries, keys and values h times with different learned linear projections to dimensions d_k, d_v, and d_k respectively.",
            "ground_truth": "It linearly projects queries, keys, and values h times with different learned projections.",
            "contexts": [_EXCERPTS["multi_head"]],
        },
        # --- Edge cases (2 cases) ---
        {
            "question": "What is the Transformer?",
            "answer": "The Transformer is a new simple network architecture based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.",
            "ground_truth": "A simple network architecture based solely on attention mechanisms.",
            "contexts": [_EXCERPTS["abstract"]],
        },
        {
            "question": "attention mechanism transformer",
            "answer": "The Transformer uses Scaled Dot-Product Attention and Multi-Head Attention. An attention function maps a query and key-value pairs to an output computed as a weighted sum of values.",
            "ground_truth": "The Transformer uses attention mechanisms including Scaled Dot-Product and Multi-Head Attention.",
            "contexts": [_EXCERPTS["attention_def"], _EXCERPTS["scaled_dot_product"], _EXCERPTS["multi_head"]],
        },
        # --- Deliberately bad answer (hallucinated) ---
        {
            "question": "What architecture is the Transformer based on?",
            "answer": "The Transformer is based on a complex recurrent neural network with long short-term memory units that process tokens sequentially.",
            "ground_truth": "The Transformer is based solely on attention mechanisms.",
            "contexts": [_EXCERPTS["abstract"]],
        },
    ]


_EVIDENCE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", ".omo", "evidence")
_CSV_PATH = os.path.join(_EVIDENCE_DIR, "ragas_results.csv")


def run_evaluation(records: list[dict]) -> dict:
    ds = Dataset.from_list(records)
    metrics = [
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    ]
    result = evaluate(ds, metrics=metrics)
    df = result.to_pandas()
    print("\n=== RAGAS Evaluation Results ===")
    print(df.describe())
    print()
    print(df.to_string(index=False))

    os.makedirs(_EVIDENCE_DIR, exist_ok=True)
    df.to_csv(_CSV_PATH, index=False)
    print(f"\nResults exported to {_CSV_PATH}")

    return result


def compare_evaluations(records: list[dict], runs: int = 2):
    print(f"\n--- Running {runs} evaluations for comparison ---\n")
    all_dfs = []
    for i in range(runs):
        print(f"[Run {i + 1}/{runs}]")
        result = run_evaluation(records)
        df = result.to_pandas()
        df.insert(0, "run", i + 1)
        all_dfs.append(df)

    import pandas as pd

    combined = pd.concat(all_dfs, ignore_index=True)
    grouped = combined.drop(columns=["run"]).groupby(level=0)
    means = grouped.mean()
    stds = grouped.std()

    print("\n=== Comparison: Mean Scores ===")
    print(means.to_string())
    print("\n=== Comparison: Std Dev ===")
    print(stds.to_string())

    diff = means.max(axis=1) - means.min(axis=1)
    print(f"\nMax score drift across runs: {diff.max():.4f}")

    os.makedirs(_EVIDENCE_DIR, exist_ok=True)
    comparison_path = os.path.join(_EVIDENCE_DIR, "ragas_comparison.csv")
    combined.to_csv(comparison_path, index=False)
    print(f"\nComparison exported to {comparison_path}")


def main():
    parser = argparse.ArgumentParser(description="RAGAS batch evaluation for Paper Pilot")
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Run evaluation N times and diff scores for A/B comparison",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=2,
        help="Number of evaluation runs for --compare (default: 2)",
    )
    args = parser.parse_args()

    records = load_dataset()
    print(f"Loaded {len(records)} test cases from golden dataset")

    if args.compare:
        compare_evaluations(records, runs=args.runs)
    else:
        run_evaluation(records)


if __name__ == "__main__":
    main()
