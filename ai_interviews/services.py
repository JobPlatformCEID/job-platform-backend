import httpx
from django.conf import settings
from pathlib import Path
from groq import Groq
import logging
from google import genai

PROMPTS_DIR = Path(__file__).parent / 'prompts'

def _read_prompt(filename):
    return (PROMPTS_DIR / filename).read_text(encoding='utf-8').strip()

SUMMARY_THRESHOLD = 16

SYSTEM_PROMPT = _read_prompt('system_prompt.txt')
OPENING_PROMPT = _read_prompt('opening_prompt.txt')
SUMMARY_PROMPT = _read_prompt('summary_prompt.txt')

logger = logging.getLogger(__name__)

def _job_context(session) -> dict:
    posting = session.job_posting
    requirements = posting.requirements.strip() if posting.requirements else "Δεν έχουν δοθεί συγκεκριμένες απαιτήσεις."

    return {
        "job_title": posting.title,
        "job_description": posting.description.strip(),
        "job_requirements": requirements,
        "job_context": (
            f"Τίτλος αγγελίας: {posting.title}\n"
            f"Περιγραφή αγγελίας:\n{posting.description.strip()}\n\n"
            f"Απαιτήσεις αγγελίας:\n{requirements}"
        ),
    }

def _inject_vars(prompt: str, session) -> str:
    return prompt.format(**_job_context(session))

def get_system_prompt(session):
    return _inject_vars(SYSTEM_PROMPT, session)

def build_messages(session, history):
    messages = [{"role": "system", "content": get_system_prompt(session)}]
    messages.extend(history)
    return messages


def _route(messages):
    if settings.AI_BACKEND == "groq":
        return _groq_response(messages)
    elif settings.AI_BACKEND == "gemini":
        return _gemini_response(messages)
    return _ollama_response(messages)


def get_ai_response(session, history):
    return _route(build_messages(session, history))


def get_opening_message(session):
    messages = [
        {"role": "system", "content": get_system_prompt(session)},
        {"role": "user", "content": _inject_vars(OPENING_PROMPT, session)},
    ]
    return _route(messages)


def summarize_history(session, history):
    messages = [
        {"role": "system", "content": get_system_prompt(session)},
        *history,
        {"role": "user", "content": _inject_vars(SUMMARY_PROMPT, session)},
    ]
    return _route(messages)


def _log_tokens(provider: str, prompt: int, completion: int, total: int) -> None:
    logger.info(f"Tokens ({provider}): prompt={prompt} completion={completion} total={total}")


def _groq_response(messages):
    logger.info(f"Using Groq model: {settings.AI_GROQ_MODEL}")
    client = Groq(api_key=settings.GROQ_API_KEY)
    response = client.chat.completions.create(
        model=settings.AI_GROQ_MODEL,
        messages=messages,
        temperature=0.4,
    )
    usage = response.usage
    _log_tokens("groq", usage.prompt_tokens, usage.completion_tokens, usage.total_tokens)
    return response.choices[0].message.content


def _gemini_response(messages):
    logger.info(f"Using Gemini model: {settings.AI_GEMINI_MODEL}")
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    # Extract system prompt and conversation separately
    system_prompt = next(
        (m["content"] for m in messages if m["role"] == "system"), None
    )
    conversation = [m for m in messages if m["role"] != "system"]

    # Convert to Gemini format
    gemini_contents = [
        {"role": "model" if m["role"] == "assistant" else "user",
         "parts": [{"text": m["content"]}]}
        for m in conversation
    ]

    response = client.models.generate_content(
        model=settings.AI_GEMINI_MODEL,
        contents=gemini_contents,
        config={
            "system_instruction": system_prompt,
            "temperature": 0.4,
        }
    )
    usage = getattr(response, "usage_metadata", None)
    if usage:
        _log_tokens(
            "gemini",
            getattr(usage, "prompt_token_count", 0) or 0,
            getattr(usage, "candidates_token_count", 0) or 0,
            getattr(usage, "total_token_count", 0) or 0,
        )
    return response.text


def _ollama_response(messages):
    logger.info(f"Using local model: {settings.AI_LOCAL_MODEL}")
    response = httpx.post(
        f"{settings.AI_LOCAL_ENDPOINT}/v1/chat/completions",
        json={
            "model": settings.AI_LOCAL_MODEL,
            "messages": messages,
            "stream": False,
        },
        timeout=60.0
    )
    response.raise_for_status()
    data = response.json()
    usage = data.get("usage")
    if usage:
        _log_tokens(
            "local",
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
            usage.get("total_tokens", 0),
        )
    return data["choices"][0]["message"]["content"]
