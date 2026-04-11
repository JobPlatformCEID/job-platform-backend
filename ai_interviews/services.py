import httpx
from django.conf import settings
import os

# --- AI BACKEND CONFIGURATION ---
AI_BACKEND = settings.AI_BACKEND
OLLAMA_HOST = settings.OLLAMA_HOST
OLLAMA_MODEL = settings.OLLAMA_MODEL
GROQ_API_KEY = settings.GROQ_API_KEY
GROQ_MODEL = settings.GROQ_MODEL

PROMPTS_DIR = PROMPTS_DIR = os.path.join(os.path.dirname(__file__), 'prompts')

def _read_prompt(filename):
    with open(os.path.join(PROMPTS_DIR, filename), 'r', encoding='utf-8') as f:
        return f.read().strip()

# --- SUMMARY TRIGGER ---
SUMMARY_THRESHOLD = 16  # change this to trigger summary at different message counts

# --- SYSTEM PROMPTS ---
SYSTEM_PROMPT = _read_prompt('system_prompt.txt')
OPENING_PROMPT = _read_prompt('opening_prompt.txt')
SUMMARY_PROMPT = _read_prompt('sumary_prompt.txt')


def get_system_prompt(session):
    return SYSTEM_PROMPT + f"\n\nJOB ROLE: The candidate is interviewing for the position: {session.job_role}. Tailor your questions accordingly."

def build_messages(session, history):
    messages = [{"role": "system", "content": get_system_prompt(session)}]
    messages.extend(history)
    return messages


def get_ai_response(session, history):
    messages = build_messages(session, history)
    if AI_BACKEND == "groq":
        return _groq_response(messages)
    return _ollama_response(messages)


def get_opening_message(session):
    messages = [
        {"role": "system", "content": get_system_prompt(session)},
        {"role": "user", "content": OPENING_PROMPT},
    ]
    if AI_BACKEND == "groq":
        return _groq_response(messages)
    return _ollama_response(messages)


def summarize_history(session, history):
    messages = [
        {"role": "system", "content": get_system_prompt(session)},
        *history,
        {"role": "user", "content": SUMMARY_PROMPT},
    ]
    if AI_BACKEND == "groq":
        return _groq_response(messages)
    return _ollama_response(messages)


import logging
logger = logging.getLogger(__name__)

def _groq_response(messages):
    from groq import Groq
    logger.info(f"Using Groq model: {GROQ_MODEL}")
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages
    )
    return response.choices[0].message.content


import logging
logger = logging.getLogger(__name__)

def _groq_response(messages):
    from groq import Groq
    logger.info(f"Using Groq model: {GROQ_MODEL}")
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages
    )
    return response.choices[0].message.content


def _ollama_response(messages):
    logger.info(f"Using Groq model: {OLLAMA_MODEL}")
    response = httpx.post(
        f"{OLLAMA_HOST}/v1/chat/completions",
        json={
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
        },
        timeout=60.0
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
