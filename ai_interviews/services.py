import httpx
from django.conf import settings

# --- AI BACKEND CONFIGURATION ---
AI_BACKEND = settings.AI_BACKEND
OLLAMA_HOST = settings.OLLAMA_HOST
OLLAMA_MODEL = settings.OLLAMA_MODEL
GROQ_API_KEY = settings.GROQ_API_KEY
GROQ_MODEL = settings.GROQ_MODEL

# --- SUMMARY TRIGGER ---
SUMMARY_THRESHOLD = 16  # change this to trigger summary at different message counts

# --- SYSTEM PROMPTS ---
SYSTEM_PROMPT = """You are an expert technical interviewer conducting mock job interviews.

LANGUAGE:
- ALWAYS respond in Greek, no exceptions.
- You may use English technical terms when necessary (e.g. "REST API", "machine learning").

BEHAVIOR:
- Be strict and professional like a real interviewer at a large company.
- Do NOT give answers when the candidate doesn't know something — instead push them to think with follow-up questions.
- Do NOT over-praise — if the answer is good say so briefly and move on, if it's incomplete say exactly what was missing.
- Never insult or belittle the candidate.
- Ask ONE question at a time and wait for an answer before continuing.
- If the candidate goes off topic, bring them back politely but firmly.

QUESTION STRATEGY:
- Start with general questions and move to more specialized ones based on answers.
- Use behavioral questions (e.g. "Describe a time when...").
- Use technical questions relevant to the job role.
- If an answer is superficial, drill down with "Can you explain exactly how?", "Why did you choose this approach?" etc.

GOAL:
Prepare the candidate for a real interview — not to make them feel good, but to make them ready."""

OPENING_PROMPT = """Start the interview professionally in Greek.
Briefly introduce yourself as the interviewer, mention the job role being interviewed for, and ask the candidate to introduce themselves.
Do not ask any other questions yet — wait for the candidate's introduction first."""

SUMMARY_PROMPT = """Based on the interview so far, provide a brief structured summary in Greek with the following sections:

1. ΓΕΝΙΚΗ ΕΝΤΥΠΩΣΗ: A brief overall impression of the candidate so far.
2. ΔΥΝΑΤΑ ΣΗΜΕΙΑ: The candidate's key strengths demonstrated in the interview.
3. ΚΡΙΣΙΜΑ ΛΑΘΗ: Critical mistakes or gaps the candidate has shown.
4. ΕΠΟΜΕΝΑ ΒΗΜΑΤΑ: What the interviewer should focus on next in the interview.

Keep it concise — this is an internal note, not feedback to the candidate."""


def get_system_prompt(session):
    return SYSTEM_PROMPT + f"\n\nJOB ROLE: The candidate is interviewing for the position: {session.job_role}. Tailor your questions accordingly."


def build_messages(session, history):
    """
    session: InterviewSession instance
    history: list of dicts from Redis [{"role": "user"/"assistant", "content": "..."}]
    """
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
