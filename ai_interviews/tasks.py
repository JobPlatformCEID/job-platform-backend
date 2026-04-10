# Tasks.py is in charge of
# building the conversation history from db or reddis
# calling ai via services.py
# saving response to db (or reddis)
# pushing the ai response to frontend via websocket to be less taxing on the backend

import json
import logging
from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
import redis

from .models import InterviewSession, Message
from .services import get_ai_response, summarize_history, SUMMARY_THRESHOLD

logger = logging.getLogger(__name__)

# --- REDIS CLIENT ---
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0,
    decode_responses=True
)

HISTORY_KEY = "interview:session:{}:history"
SUMMARY_KEY = "interview:session:{}:summary"


# --- HISTORY MANAGEMENT ---
# get conversation history from reddis to initialise , fallsback to db if it isnt there
def get_history(session_id):
    key = HISTORY_KEY.format(session_id)
    cached = redis_client.get(key)

    if cached:
        logger.debug(f"Cache hit for session {session_id}")
        return json.loads(cached)

    logger.debug(f"Cache miss for session {session_id} — rebuilding from PostgreSQL")
    messages = Message.objects.filter(
        session_id=session_id
    ).order_by('-created_at')[:SUMMARY_THRESHOLD]

    history = [
        {"role": msg.role, "content": msg.content}
        for msg in reversed(messages)
    ]

    redis_client.set(key, json.dumps(history), ex=60*60*24)
    return history

# append a message to redis
def append_to_history(session_id, role, content):
    key = HISTORY_KEY.format(session_id)
    cached = redis_client.get(key)
    history = json.loads(cached) if cached else []

    history.append({"role": role, "content": content})
    redis_client.set(key, json.dumps(history), ex=60*60*24)

    return len(history)

    
# Summarize history when it hits SUMMARY_THRESHOLD. Replaces full history in Redis with summary + last 4 messages.
def compress_history(session, history):

    logger.info(f"Compressing history for session {session.id}")
    summary = summarize_history(session, history)

    # Keep last 4 messages for immediate context
    recent = history[-4:]

    # Store summary separately
    redis_client.set(
        SUMMARY_KEY.format(session.id),
        summary,
        ex=60*60*24
    )

    # Replace history with summary message + recent messages
    compressed = [
        {"role": "system", "content": f"ΣΥΝΟΨΗ ΣΥΝΕΝΤΕΥΞΗΣ ΩΣ ΤΩΡΑ:\n{summary}"},
        *recent
    ]

    redis_client.set(
        HISTORY_KEY.format(session.id),
        json.dumps(compressed),
        ex=60*60*24
    )

    return compressed

# Clear Redis cache for a session when deleted.
def invalidate_history(session_id):
    redis_client.delete(HISTORY_KEY.format(session_id))
    redis_client.delete(SUMMARY_KEY.format(session_id))


# --- CELERY TASK ---

@shared_task(bind=True, max_retries=3)
def generate_ai_response(self, session_id, room_group_name):
    channel_layer = get_channel_layer()

    try:
        session = InterviewSession.objects.get(id=session_id)

        # 1. Get history from Redis
        history = get_history(session_id)

        # 2. Check if we need to summarize
        if len(history) >= SUMMARY_THRESHOLD:
            history = compress_history(session, history)

        # 3. Call AI
        ai_content = get_ai_response(session, history)

        # 4. Save AI response to PostgreSQL
        ai_msg = Message.objects.create(
            session=session,
            role=Message.Role.Assistant,
            content=ai_content
        )

        # 5. Append AI response to Redis
        append_to_history(session_id, Message.Role.Assistant, ai_content)

        # 6. Push response to WebSocket
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                "type": "ai_message",
                "message": {
                    "id": ai_msg.id,
                    "role": ai_msg.role,
                    "content": ai_msg.content,
                    "created_at": ai_msg.created_at.isoformat(),
                }
            }
        )

    except InterviewSession.DoesNotExist:
        logger.error(f"Session {session_id} not found")

    except Exception as exc:
        logger.error(f"Error generating AI response for session {session_id}: {exc}")
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                "type": "error",
                "message": "Κάτι πήγε στραβά, παρακαλώ δοκίμασε ξανά."
            }
        )
        raise self.retry(exc=exc, countdown=5)