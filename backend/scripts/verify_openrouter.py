import os
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from app.config import settings

    api_key = settings.OPENROUTER_API_KEY
except Exception:
    api_key = os.getenv("OPENROUTER_API_KEY", "")

MODEL_IDS = [
    "openrouter/free",
    "nvidia/nemotron-3-embed-1b:free",
    "nvidia/llama-nemotron-rerank-vl-1b-v2:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
]


def check_models() -> bool:
    url = "https://openrouter.ai/api/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    try:
        resp = httpx.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
    except Exception as exc:
        print(f"FAIL: Could not fetch models — {exc}")
        return False

    data = resp.json()
    models = data.get("data", [])

    all_ok = True
    available_ids = {m.get("id") for m in models}

    for model_id in MODEL_IDS:
        if model_id not in available_ids:
            print(f"FAIL: {model_id} — not found in model list")
            all_ok = False
            continue

        model = next(m for m in models if m.get("id") == model_id)
        pricing = model.get("pricing", {})
        prompt_price = pricing.get("prompt", "?")
        completion_price = pricing.get("completion", "?")

        if prompt_price == "0" and completion_price == "0":
            print(f"PASS: {model_id} — free")
        else:
            print(f"WARN: {model_id} — not free (prompt={prompt_price}, completion={completion_price})")
            all_ok = False

    return all_ok


def test_chat_openai() -> None:
    if not api_key:
        print("SKIP: ChatOpenAI test — no OPENROUTER_API_KEY set")
        return

    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model="openrouter/free",
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            max_tokens=20,
        )
        result = llm.invoke("say hi")
        print(f"PASS: ChatOpenAI returned — {result.content!r}")
    except Exception as exc:
        print(f"FAIL: ChatOpenAI test — {exc}")


def main() -> None:
    print("=" * 60)
    print("OpenRouter Verification")
    print("=" * 60)

    print("\n--- Model ID checks ---")
    models_ok = check_models()

    print("\n--- ChatOpenAI invocation ---")
    test_chat_openai()

    print("\n" + "=" * 60)
    if models_ok:
        print("RESULT: All model checks passed")
    else:
        print("RESULT: Some model checks failed (see above)")
        sys.exit(1)


if __name__ == "__main__":
    main()
