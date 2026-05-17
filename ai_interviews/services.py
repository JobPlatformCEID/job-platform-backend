import httpx
from django.conf import settings
from pathlib import Path
import logging
from groq import Groq

PROMPTS_DIR = Path(__file__).parent / 'prompts'

def _read_prompt(filename):
    return (PROMPTS_DIR / filename).read_text(encoding='utf-8').strip()

SUMMARY_THRESHOLD = 16

SYSTEM_PROMPT = _read_prompt('system_prompt.txt')
OPENING_PROMPT = _read_prompt('opening_prompt.txt')
SUMMARY_PROMPT = _read_prompt('summary_prompt.txt')

logger = logging.getLogger(__name__)

def _candidate_context(session) -> dict:
    user = session.user
    profile = getattr(user, 'candidate_profile', None)

    if profile is None:
        return {
            "candidate_skills": "Δεν υπάρχουν καταχωρημένες δεξιότητες.",
            "candidate_experience": "Δεν υπάρχει καταχωρημένη εμπειρία.",
            "candidate_education": "Δεν υπάρχει καταχωρημένη εκπαίδευση.",
            "candidate_context": "Δεν υπάρχουν διαθέσιμα στοιχεία υποψηφίου.",
        }

    skills = profile.skills.all()
    skills_text = ", ".join(s.name for s in skills) if skills else "Δεν υπάρχουν καταχωρημένες δεξιότητες."

    experiences = profile.work_experiences.all()
    if experiences:
        exp_lines = []
        for e in experiences:
            end = e.end_date.strftime("%m/%Y") if e.end_date else "Σήμερα"
            exp_lines.append(
                f"- {e.title} @ {e.company} ({e.start_date.strftime('%m/%Y')}–{end})"
                + (f" [{e.get_employment_type_display()}]" if e.employment_type else "")
                + (f"\n  {e.description}" if e.description else "")
            )
        experience_text = "\n".join(exp_lines)
    else:
        experience_text = "Δεν υπάρχει καταχωρημένη εμπειρία."

    educations = profile.educations.all()
    if educations:
        edu_lines = []
        for e in educations:
            grad = f" ({e.graduation_date.strftime('%m/%Y')})" if e.graduation_date else ""
            edu_lines.append(f"- {e.degree} – {e.institution} [{e.get_level_display()}]{grad}")
        education_text = "\n".join(edu_lines)
    else:
        education_text = "Δεν υπάρχει καταχωρημένη εκπαίδευση."

    candidate_context = (
        f"Δεξιότητες:\n{skills_text}\n\n"
        f"Επαγγελματική Εμπειρία:\n{experience_text}\n\n"
        f"Εκπαίδευση:\n{education_text}"
    )

    return {
        "candidate_skills": skills_text,
        "candidate_experience": experience_text,
        "candidate_education": education_text,
        "candidate_context": candidate_context,
    }

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
    return prompt.format(**_job_context(session), **_candidate_context(session))

def get_system_prompt(session):
    prompt = _inject_vars(SYSTEM_PROMPT, session)
    #debug info just to make sure that the vars are indeed in the system prompt
    #logger.info("System prompt:\n%s", prompt)
    return prompt

def build_messages(session, history):
    messages = [{"role": "system", "content": get_system_prompt(session)}]
    messages.extend(history)
    return messages

def _route(messages):
    if settings.AI_BACKEND == "groq":
        return _groq_response(messages)
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
    if usage:
        _log_tokens(
            "groq",
            usage.prompt_tokens,
            usage.completion_tokens,
            usage.total_tokens,
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
