import os
import pytest
from deepeval import assert_test
from deepeval.dataset import EvaluationDataset
from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    FaithfulnessMetric,
)
from deepeval.models import OpenRouterModel
from deepeval.test_case import LLMTestCase

_api_key = os.environ.get("OPENROUTER_API_KEY")
if not _api_key:
    pytest.skip("OPENROUTER_API_KEY not set — skipping all DeepEval tests", allow_module_level=True)

def _judge():
    return OpenRouterModel(model="openai/gpt-4o-mini", api_key=_api_key)

_faithfulness = FaithfulnessMetric(threshold=0.85, model=_judge())
_answer_relevancy = AnswerRelevancyMetric(threshold=0.8, model=_judge())
_contextual_precision = ContextualPrecisionMetric(threshold=0.7, model=_judge())
_contextual_recall = ContextualRecallMetric(threshold=0.7, model=_judge())

_metrics = [_faithfulness, _answer_relevancy, _contextual_precision, _contextual_recall]
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

# ---------------------------------------------------------------------------
# Test case definitions  (25 golden + 1 deliberately bad = 26 total)
# ---------------------------------------------------------------------------
_test_cases = [
    # --- Directly answerable from paper (10 cases) ---
    LLMTestCase(
        input="What architecture is the Transformer based on?",
        actual_output="The Transformer is based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.",
        expected_output="The Transformer is based solely on attention mechanisms, without recurrence or convolutions.",
        retrieval_context=[_EXCERPTS["abstract"]],
    ),
    LLMTestCase(
        input="What BLEU score does the Transformer achieve on WMT 2014 English-to-German?",
        actual_output="The Transformer achieves 28.4 BLEU on the WMT 2014 English-to-German translation task.",
        expected_output="28.4 BLEU on WMT 2014 English-to-German.",
        retrieval_context=[_EXCERPTS["results"]],
    ),
    LLMTestCase(
        input="What is Scaled Dot-Product Attention?",
        actual_output="Scaled Dot-Product Attention takes queries and keys of dimension d_k and values of dimension d_v, computes dot products of the query with all keys, divides by sqrt(d_k), and applies softmax to obtain weights on the values.",
        expected_output="An attention mechanism where the input consists of queries and keys of dimension d_k, and values of dimension d_v, computing dot products divided by sqrt(d_k) with a softmax.",
        retrieval_context=[_EXCERPTS["scaled_dot_product"]],
    ),
    LLMTestCase(
        input="Why does the Transformer need positional encoding?",
        actual_output="The Transformer needs positional encoding because it contains no recurrence and no convolution, so it must inject information about the relative or absolute position of tokens in the sequence.",
        expected_output="Because the model has no recurrence or convolution, positional information must be injected separately.",
        retrieval_context=[_EXCERPTS["positional_encoding"]],
    ),
    LLMTestCase(
        input="What are the dominant sequence transduction models?",
        actual_output="The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder.",
        expected_output="Complex recurrent or convolutional neural networks with an encoder and decoder.",
        retrieval_context=[_EXCERPTS["abstract"]],
    ),
    LLMTestCase(
        input="What is Multi-Head Attention?",
        actual_output="Multi-Head Attention linearly projects the queries, keys and values h times with different learned linear projections to d_k, d_v and d_k dimensions respectively, instead of performing a single attention function.",
        expected_output="Multiple parallel attention heads created by linearly projecting queries, keys, and values h times with different learned projections.",
        retrieval_context=[_EXCERPTS["multi_head"]],
    ),
    LLMTestCase(
        input="What are the inputs to Scaled Dot-Product Attention?",
        actual_output="The inputs consist of queries and keys of dimension d_k, and values of dimension d_v.",
        expected_output="Queries and keys of dimension d_k, and values of dimension d_v.",
        retrieval_context=[_EXCERPTS["scaled_dot_product"]],
    ),
    LLMTestCase(
        input="How much does the Transformer improve over existing models on WMT 2014?",
        actual_output="The Transformer improves over the existing best results, including ensembles, by over 2 BLEU on the WMT 2014 English-to-German translation task.",
        expected_output="It improves by over 2 BLEU over existing best results including ensembles.",
        retrieval_context=[_EXCERPTS["results"]],
    ),
    LLMTestCase(
        input="What is an attention function?",
        actual_output="An attention function maps a query and a set of key-value pairs to an output, where the query, keys, values, and output are all vectors. The output is a weighted sum of the values.",
        expected_output="A function that maps a query and key-value pairs to a vector output computed as a weighted sum of the values.",
        retrieval_context=[_EXCERPTS["attention_def"]],
    ),
    LLMTestCase(
        input="What networks are state of the art for sequence modeling?",
        actual_output="Recurrent neural networks, long short-term memory and gated recurrent neural networks have been established as state of the art for sequence modeling and transduction problems.",
        expected_output="RNNs, LSTM, and GRU are state of the art for sequence modeling and transduction.",
        retrieval_context=[_EXCERPTS["intro"]],
    ),
    # --- Synthesis across sections (5 cases) ---
    LLMTestCase(
        input="How does the Transformer avoid sequential computation?",
        actual_output="The Transformer avoids sequential computation by using attention mechanisms instead of recurrence. It processes all tokens in parallel through self-attention, dispensing with the sequential nature of RNNs entirely.",
        expected_output="By using attention mechanisms instead of recurrence, allowing parallel processing of all tokens.",
        retrieval_context=[_EXCERPTS["abstract"], _EXCERPTS["positional_encoding"]],
    ),
    LLMTestCase(
        input="Explain the components of the Transformer's attention mechanism.",
        actual_output="The Transformer uses Scaled Dot-Product Attention and Multi-Head Attention. Scaled Dot-Product Attention computes weighted sums via dot products scaled by sqrt(d_k). Multi-Head Attention runs multiple attention functions in parallel with different linear projections.",
        expected_output="Scaled Dot-Product Attention for computing attention weights and Multi-Head Attention for parallel attention functions.",
        retrieval_context=[_EXCERPTS["scaled_dot_product"], _EXCERPTS["multi_head"]],
    ),
    LLMTestCase(
        input="Why is the Transformer considered simpler than previous models?",
        actual_output="The Transformer is simpler because it dispenses with recurrence and convolutions entirely, relying solely on attention mechanisms. Previous models required complex RNN or CNN architectures.",
        expected_output="It dispenses with recurrence and convolutions, using only attention mechanisms.",
        retrieval_context=[_EXCERPTS["abstract"]],
    ),
    LLMTestCase(
        input="How does the Transformer handle token position?",
        actual_output="Since the Transformer has no recurrence or convolution, it injects information about the relative or absolute position of tokens in the sequence through positional encoding.",
        expected_output="Through positional encoding that injects relative or absolute position information.",
        retrieval_context=[_EXCERPTS["positional_encoding"]],
    ),
    LLMTestCase(
        input="What makes the Transformer architecture novel?",
        actual_output="The Transformer is novel because it is based solely on attention mechanisms, completely dispensing with recurrence and convolutions that were the foundation of previous sequence transduction models.",
        expected_output="Its use of only attention mechanisms without recurrence or convolutions.",
        retrieval_context=[_EXCERPTS["abstract"], _EXCERPTS["intro"]],
    ),
    # --- Unrelated topics (5 cases) ---
    LLMTestCase(
        input="What is backpropagation?",
        actual_output="The provided excerpts discuss the Transformer architecture for sequence transduction but do not cover backpropagation. Based solely on the given excerpts, I cannot provide information about backpropagation.",
        expected_output="The provided excerpts do not discuss backpropagation.",
        retrieval_context=[_EXCERPTS["abstract"]],
    ),
    LLMTestCase(
        input="How does gradient descent work?",
        actual_output="The provided excerpts focus on the Transformer architecture and attention mechanisms but do not cover gradient descent. Based solely on the given excerpts, I cannot provide information about gradient descent.",
        expected_output="The provided excerpts do not discuss gradient descent.",
        retrieval_context=[_EXCERPTS["intro"]],
    ),
    LLMTestCase(
        input="What is the difference between CNN and RNN?",
        actual_output="The provided excerpts mention that both convolutional and recurrent neural networks are used in sequence transduction models, but do not explain the differences between them. Based solely on the given excerpts, I cannot detail the differences.",
        expected_output="The excerpts do not detail the differences between CNN and RNN.",
        retrieval_context=[_EXCERPTS["abstract"]],
    ),
    LLMTestCase(
        input="Explain transfer learning.",
        actual_output="The provided excerpts discuss sequence transduction models and the Transformer architecture but do not cover transfer learning. Based solely on the given excerpts, I cannot provide information about transfer learning.",
        expected_output="The provided excerpts do not discuss transfer learning.",
        retrieval_context=[_EXCERPTS["intro"]],
    ),
    LLMTestCase(
        input="What is batch normalization?",
        actual_output="The provided excerpts discuss the Transformer architecture and attention mechanisms but do not cover batch normalization. Based solely on the given excerpts, I cannot provide information about batch normalization.",
        expected_output="The provided excerpts do not discuss batch normalization.",
        retrieval_context=[_EXCERPTS["abstract"]],
    ),
    # --- Citation requirements (3 cases) ---
    LLMTestCase(
        input="What specific BLEU score does the Transformer achieve and on which task?",
        actual_output="The Transformer achieves 28.4 BLEU on the WMT 2014 English-to-German translation task, improving over existing best results by over 2 BLEU.",
        expected_output="28.4 BLEU on WMT 2014 English-to-German, improving by over 2 BLEU.",
        retrieval_context=[_EXCERPTS["results"]],
    ),
    LLMTestCase(
        input="What is the key innovation of the Transformer architecture?",
        actual_output="The key innovation is that the Transformer is based solely on attention mechanisms, completely eliminating recurrence and convolutions from the architecture.",
        expected_output="Being based solely on attention mechanisms without recurrence or convolutions.",
        retrieval_context=[_EXCERPTS["abstract"]],
    ),
    LLMTestCase(
        input="How does Multi-Head Attention project its inputs?",
        actual_output="Multi-Head Attention linearly projects the queries, keys and values h times with different learned linear projections to dimensions d_k, d_v, and d_k respectively.",
        expected_output="It linearly projects queries, keys, and values h times with different learned projections.",
        retrieval_context=[_EXCERPTS["multi_head"]],
    ),
    # --- Edge cases (2 cases) ---
    LLMTestCase(
        input="What is the Transformer?",
        actual_output="The Transformer is a new simple network architecture based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.",
        expected_output="A simple network architecture based solely on attention mechanisms.",
        retrieval_context=[_EXCERPTS["abstract"]],
    ),
    LLMTestCase(
        input="attention mechanism transformer",
        actual_output="The Transformer uses Scaled Dot-Product Attention and Multi-Head Attention. An attention function maps a query and key-value pairs to an output computed as a weighted sum of values.",
        expected_output="The Transformer uses attention mechanisms including Scaled Dot-Product and Multi-Head Attention.",
        retrieval_context=[_EXCERPTS["attention_def"], _EXCERPTS["scaled_dot_product"], _EXCERPTS["multi_head"]],
    ),
]

# ---------------------------------------------------------------------------
# Deliberately bad answer — hallucinated, contradicts the retrieval context
# ---------------------------------------------------------------------------
_bad_test_case = LLMTestCase(
    input="What architecture is the Transformer based on?",
    actual_output="The Transformer is based on a complex recurrent neural network with long short-term memory units that process tokens sequentially.",
    expected_output="The Transformer is based solely on attention mechanisms.",
    retrieval_context=[_EXCERPTS["abstract"]],
)

# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------
_dataset = EvaluationDataset(alias="Paper Pilot RAG Quality", test_cases=_test_cases)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("test_case", _dataset.test_cases)
def test_rag_quality(test_case: LLMTestCase):
    assert_test(test_case, _metrics)


def test_bad_answer_scores_below_threshold():
    _faithfulness.measure(_bad_test_case)
    assert _faithfulness.score < 0.5, (
        f"Expected faithfulness < 0.5 for hallucinated answer, got {_faithfulness.score}"
    )