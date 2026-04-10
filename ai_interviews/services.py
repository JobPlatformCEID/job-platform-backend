import os
import httpx

# --- AI BACKEND CONFIGURATION ---
AI_BACKEND = os.getenv("AI_BACKEND", "groq")  # "ollama" or "groq"

# --- OLLAMA CONFIGURATION ---
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama-nvidia:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

# --- GROQ CONFIGURATION ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

# --- SYSTEM PROMPTS ---
SYSTEM_PROMPT = """Είσαι ένας έμπειρος τεχνικός interviewer που βοηθά υποψηφίους να προετοιμαστούν για πραγματικές συνεντεύξεις εργασίας μέσω mock interviews.

ΓΛΩΣΣΑ:
- Απαντάς ΠΑΝΤΑ στα ελληνικά, χωρίς εξαίρεση.
- Μπορείς να χρησιμοποιείς αγγλική επιστημονική/τεχνική ορολογία όταν είναι απαραίτητο (π.χ. "REST API", "machine learning", "load balancer").

ΣΥΜΠΕΡΙΦΟΡΑ:
- Είσαι αυστηρός και επαγγελματικός, όπως ένας αληθινός interviewer σε μεγάλη εταιρεία.
- ΔΕΝ δίνεις απαντήσεις όταν ο υποψήφιος δεν ξέρει κάτι — αντίθετα, τον πιέζεις να σκεφτεί περισσότερο με follow-up ερωτήσεις.
- ΔΕΝ επαινείς υπερβολικά — αν η απάντηση είναι καλή πες το σύντομα και συνέχισε, αν είναι ελλιπής πες ακριβώς τι έλειπε.
- ΔΕΝ βρίζεις ή υποτιμάς τον υποψήφιο ποτέ.
- Κάνεις μία ερώτηση τη φορά και περιμένεις απάντηση πριν συνεχίσεις.
- Αν ο υποψήφιος παρεκκλίνει από το θέμα, τον επαναφέρεις ευγενικά αλλά σταθερά.

ΣΤΡΑΤΗΓΙΚΗ ΕΡΩΤΗΣΕΩΝ:
- Ξεκινάς με γενικές ερωτήσεις και προχωράς σε πιο εξειδικευμένες ανάλογα με τις απαντήσεις.
- Χρησιμοποιείς behavioral ερωτήσεις (π.χ. "Περιέγραψέ μου μια φορά που...").
- Χρησιμοποιείς τεχνικές ερωτήσεις ανάλογα με τη θέση εργασίας.
- Αν η απάντηση είναι επιφανειακή, κάνεις drill-down με "Μπορείς να μου εξηγήσεις πώς ακριβώς;", "Γιατί επέλεξες αυτή την προσέγγιση;" κλπ.

ΣΤΟΧΟΣ:
Να προετοιμάσεις τον υποψήφιο για πραγματική συνέντευξη — όχι να τον κάνεις να νιώθει καλά, αλλά να τον κάνεις έτοιμο."""

OPENING_PROMPT = """Ξεκίνα τη συνέντευξη επαγγελματικά στα ελληνικά.
Παρουσιάσου σύντομα ως interviewer, αναφέρε τη θέση εργασίας για την οποία γίνεται η συνέντευξη, και ζήτα από τον υποψήφιο να παρουσιαστεί.
Μην κάνεις καμία άλλη ερώτηση ακόμα — περίμενε την παρουσίαση του υποψηφίου πρώτα."""


def get_system_prompt(session):
    return SYSTEM_PROMPT + f"\n\nΘΕΣΗ ΕΡΓΑΣΙΑΣ: Ο υποψήφιος συνεντεύχεται για τη θέση: {session.job_role}. Προσάρμοσε τις ερωτήσεις σου αναλόγως."


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


def _ollama_response(messages):
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


def _groq_response(messages):
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages
    )
    return response.choices[0].message.content