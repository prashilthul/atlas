import json
import logging
import random
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

_BASE = settings.OPENROUTER_BASE_URL or "https://openrouter.ai/api/v1"

_FAITHFULNESS_PROMPT = (
    "You are evaluating an AI answer's faithfulness to provided context.\n"
    "Context: {context}\n"
    "Answer: {answer}\n"
    "Rate faithfulness 0-1 based on whether the answer is fully supported by the context.\n"
    "Return ONLY a number between 0 and 1."
)

_CITATION_ACCURACY_PROMPT = (
    "For each citation [N] in the answer, verify the cited chunk actually supports the claim.\n"
    "Answer: {answer}\n"
    "Chunks: {chunks_json}\n"
    "Return average citation accuracy as a number between 0 and 1."
)


def should_sample(error_occurred: bool = False) -> bool:
    if error_occurred:
        return True
    return random.random() < 0.05


async def _judge(prompt: str) -> float | None:
    llm = ChatOpenAI(
        model=settings.JUDGE_MODEL,
        openai_api_key=settings.OPENROUTER_API_KEY,
        openai_api_base=_BASE,
        temperature=0,
        max_tokens=10,
    )
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        text = (response.content or "").strip()
        return float(text)
    except Exception:
        logger.warning("Judge call failed (rate limit or timeout)")
        return None


async def judge_faithfulness(query: str, answer: str, chunks: list) -> float | None:
    context = "\n\n".join(c.content if hasattr(c, "content") else str(c) for c in chunks)
    prompt = _FAITHFULNESS_PROMPT.format(context=context, answer=answer)
    return await _judge(prompt)


async def judge_citation_accuracy(answer: str, chunks: list) -> float | None:
    chunks_json = json.dumps(
        [{"content": c.content, "section": c.section_heading} for c in chunks],
        ensure_ascii=False,
    )
    prompt = _CITATION_ACCURACY_PROMPT.format(answer=answer, chunks_json=chunks_json)
    return await _judge(prompt)


async def run_online_eval(
    query: str, answer: str, chunks: list, error_occurred: bool = False
) -> dict[str, Any] | None:
    if not should_sample(error_occurred):
        return None

    faithfulness = await judge_faithfulness(query, answer, chunks)
    citation_accuracy = await judge_citation_accuracy(answer, chunks)

    if faithfulness is None and citation_accuracy is None:
        return None

    return {
        "faithfulness": faithfulness,
        "citation_accuracy": citation_accuracy,
    }
