# Tasks.py is in charge of
# building the conversation history from db or redis
# calling ai via services.py
# saving response to db (or redis)
# pushing the ai response to frontend via websocket to be less taxing on the backend

import logging
from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.cache import cache

from .models import InterviewSession, InterviewMessage
from .services import get_ai_response, get_opening_message, summarize_history, SUMMARY_THRESHOLD

logger = logging.getLogger(__name__)

HISTORY_KEY = "interview:session:{}:history"
SUMMARY_KEY = "interview:session:{}:summary"


# --- HISTORY MANAGEMENT ---
# get conversation history from redis to initialise, falls back to db if it isnt there
def get_history(session_id):
    key = HISTORY_KEY.format(session_id)
    cached = cache.get(key)

    if cached is not None:
        logger.info(f"Cache hit for session {session_id}, history length: {len(cached)}")
        return cached

    logger.debug(f"Cache miss for session {session_id}, rebuilding from PostgreSQL")

    # Check if a summary exists before rebuilding
    summary = cache.get(SUMMARY_KEY.format(session_id))

    messages = InterviewMessage.objects.filter(
        session_id=session_id
    ).order_by('created_at')  # ALL messages, oldest first

    history = [{"role": m.role, "content": m.content} for m in messages]

    if summary:
        recent = history[-4:]
        history = [
            {"role": "system", "content": f"ΣΥΝΟΨΗ ΣΥΝΕΝΤΕΥΞΗΣ ΩΣ ΤΩΡΑ:\n{summary}"},
            *recent
        ]

    cache.set(key, history, timeout=60*60*24)
    logger.info(f"Rebuilt AI history for session {session_id}, history length: {len(history)}")
    return history

# append a message to redis
def append_to_history(session_id, role, content):
    key = HISTORY_KEY.format(session_id)
    history = cache.get(key) or []

    history.append({"role": role, "content": content})
    cache.set(key, history, timeout=60*60*24)

    return len(history)

    
# Summarize history when it hits SUMMARY_THRESHOLD. Replaces full history in Redis with summary + last 4 messages.
def compress_history(session, history):

    logger.info(f"Compressing history for session {session.id}")
    summary = summarize_history(session, history)

    # Keep last 4 messages for immediate context
    recent = history[-4:]

    # Store summary separately
    cache.set(
        SUMMARY_KEY.format(session.id),
        summary,
        timeout=60*60*24
    )

    # Replace history with summary message + recent messages
    compressed = [
        {"role": "system", "content": f"ΣΥΝΟΨΗ ΣΥΝΕΝΤΕΥΞΗΣ ΩΣ ΤΩΡΑ:\n{summary}"},
        *recent
    ]

    cache.set(
        HISTORY_KEY.format(session.id),
        compressed,
        timeout=60*60*24
    )

    return compressed

# Clear Redis cache for a session when deleted.
def invalidate_history(session_id):
    cache.delete(HISTORY_KEY.format(session_id))
    cache.delete(SUMMARY_KEY.format(session_id))


# --- CELERY TASK ---

@shared_task(bind=True, max_retries=3)
def generate_ai_response(self, session_id, room_group_name):
    channel_layer = get_channel_layer()

    try:
        session = InterviewSession.objects.select_related(
                    'job_posting', 'user', 'user__candidate_profile'
                ).prefetch_related(
                    'user__candidate_profile__skills',
                    'user__candidate_profile__work_experiences',
                    'user__candidate_profile__educations',
                ).get(id=session_id)

        # 1. Get history from Redis
        history = get_history(session_id)

        # 2. Check if we need to summarize
        if len(history) >= SUMMARY_THRESHOLD:
            history = compress_history(session, history)

        # 3. Call AI
        ai_content = get_ai_response(session, history)

        # 4. Save AI response to PostgreSQL
        ai_msg = InterviewMessage.objects.create(
            session=session,
            role=InterviewMessage.Role.Assistant,
            content=ai_content
        )

        # 5. Append AI response to Redis
        append_to_history(session_id, InterviewMessage.Role.Assistant, ai_content)

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
        if self.request.retries >= self.max_retries:
            async_to_sync(channel_layer.group_send)(
                room_group_name,
                {
                    "type": "error",
                    "message": "Could not generate AI response. Please try sending your message again."
                }
            )
        else:
            raise self.retry(exc=exc, countdown=2 ** self.request.retries * 5 )


@shared_task(bind=True, max_retries=3)
def generate_opening_message(self, session_id, room_group_name):
    channel_layer = get_channel_layer()

    try:
        # If opening message already exists, just re-push it
        existing = InterviewMessage.objects.filter(
            session_id=session_id,
            role=InterviewMessage.Role.Assistant
        ).first()

        if existing:
            async_to_sync(channel_layer.group_send)(
                room_group_name,
                {
                    "type": "ai_message",
                    "message": {
                        "id": existing.id,
                        "role": existing.role,
                        "content": existing.content,
                        "created_at": existing.created_at.isoformat(),
                    }
                }
            )
            return

        session = InterviewSession.objects.select_related(
                    'job_posting', 'user', 'user__candidate_profile'
                ).prefetch_related(
                    'user__candidate_profile__skills',
                    'user__candidate_profile__work_experiences',
                    'user__candidate_profile__educations',
                ).get(id=session_id)
        opening = get_opening_message(session)

        ai_msg = InterviewMessage.objects.create(
            session=session,
            role=InterviewMessage.Role.Assistant,
            content=opening
        )
        append_to_history(session_id, InterviewMessage.Role.Assistant, opening)

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
        logger.error(f"Session {session_id} not found for opening message")

    except Exception as exc:
        logger.error(f"Error generating opening message for session {session_id}: {exc}")
        if self.request.retries >= self.max_retries:
            async_to_sync(channel_layer.group_send)(
                room_group_name,
                {
                    "type": "error",
                    "message": "Could not generate opening message. You can start the conversation by typing a message."
                }
            )
        else:
            raise self.retry(exc=exc, countdown=2 ** self.request.retries * 5)
