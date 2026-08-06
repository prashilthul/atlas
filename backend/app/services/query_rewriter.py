import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

_BASE = settings.OPENROUTER_BASE_URL or "https://openrouter.ai/api/v1"

_SYSTEM_PROMPT = (
    "You rewrite a follow-up question into a standalone, self-contained question "
    "for a research paper retrieval engine. Resolve pronouns and vague references "
    "using the conversation history. Keep the user's original meaning and wording. "
    "Output only the rewritten question and nothing else."
)

_ANAPHORA = (
    " it ", " this ", " that ", " they ", " them ", " these ", " those ",
    " what about ", " the one ", " above ", " previous ", " earlier ",
)


def _truncate(text: str, limit: int = 500) -> str:
    return text if len(text) <= limit else text[:limit] + "..."


def should_rewrite(query: str, history: list[tuple[str, str]]) -> bool:
    if not history:
        return False
    if len(query) <= 100:
        return True
    padded = f" {query.lower().strip()} "
    return any(tok in padded for tok in _ANAPHORA)


async def rewrite_query(
    query: str,
    history: list[tuple[str, str]],
    model: str = "openrouter/free",
) -> str:
    if not settings.OPENROUTER_API_KEY:
        return query

    transcript = "\n".join(
        f"{role}: {_truncate(content)}" for role, content in history[-6:]
    )
    prompt = (
        f"Conversation history:\n{transcript}\n\n"
        f"Latest user question: {query}\n\n"
        f"Rewritten standalone question:"
    )

    llm = ChatOpenAI(
        model=model,
        openai_api_key=settings.OPENROUTER_API_KEY,
        openai_api_base=_BASE,
        temperature=0,
        max_tokens=80,
        request_timeout=8.0,
    )
    try:
        response = await llm.ainvoke(
            [SystemMessage(content=_SYSTEM_PROMPT), HumanMessage(content=prompt)]
        )
        rewritten = (response.content or "").strip().strip('"')
        if len(rewritten) < 10:
            return query
        return rewritten
    except Exception as exc:
        logger.warning("Query rewriting failed, using raw query: %s", exc)
        return query
