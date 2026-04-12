import httpx
from django.conf import settings
from pathlib import Path
from groq import Groq
import logging

# Prompts directory
PROMPTS_DIR = Path(__file__).parent / 'prompts'

def _read_prompt(filename):
    return (PROMPTS_DIR / filename).read_text(encoding='utf-8').strip()

# --- SUMMARY TRIGGER ---
SUMMARY_THRESHOLD = 16  # change this to trigger summary at different message counts

# --- SYSTEM PROMPTS ---
SYSTEM_PROMPT = _read_prompt('system_prompt.txt')
OPENING_PROMPT = _read_prompt('opening_prompt.txt')
SUMMARY_PROMPT = _read_prompt('sumary_prompt.txt')

logger = logging.getLogger(__name__)

def get_system_prompt(session):
    return SYSTEM_PROMPT + f"\n\nJOB ROLE: The candidate is interviewing for the position: {session.job_role}. Tailor your questions accordingly."

def build_messages(session, history):
    messages = [{"role": "system", "content": get_system_prompt(session)}]
    messages.extend(history)
    return messages


def get_ai_response(session, history):
    messages = build_messages(session, history)
    if settings.AI_BACKEND == "groq":
        return _groq_response(messages)
    return _ollama_response(messages)


def get_opening_message(session):
    messages = [
        {"role": "system", "content": get_system_prompt(session)},
        {"role": "user", "content": OPENING_PROMPT},
    ]
    if settings.AI_BACKEND == "groq":
        return _groq_response(messages)
    return _ollama_response(messages)


def summarize_history(session, history):
    messages = [
        {"role": "system", "content": get_system_prompt(session)},
        *history,
        {"role": "user", "content": SUMMARY_PROMPT},
    ]
    if settings.AI_BACKEND == "groq":
        return _groq_response(messages)
    return _ollama_response(messages)

def _groq_response(messages):
    logger.info(f"Using Groq model: {settings.AI_GROQ_MODEL}")
    client = Groq(api_key=settings.GROQ_API_KEY)
    response = client.chat.completions.create(
        model=settings.AI_GROQ_MODEL,
        messages=messages
    )
    return response.choices[0].message.content

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
    return response.json()["choices"][0]["message"]["content"]
