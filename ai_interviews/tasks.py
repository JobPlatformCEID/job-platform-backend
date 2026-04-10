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

from .models import InterviewSession , Message
from .services import get_ai_response

logger = logging.getLogger(__name__)

# redis client this will essentialy be the ais context window
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0,
    decode_responses=True
)

HISTORY_KEY = "interview:session:{}:history"
# this will later be the max amount of history before we make ai sumarise
# to save tokkens
MAX_HISTORY = 20

#check reddis for history and if we get a cache miss call db
def get_history(session_id):
    key = HISTORY_KEY.format(session_id)
    cached = redis_client.get(key)
    
    if cached:
        logger.debug(f'cache hit for session {session_id}')
        return json.loads(cached)
    
    logger.debug(f'cache miss for session {session_id} -rebuild from db')

    messages = Message.objects.filter(
        session_id = session_id,
    ).order_by('-created_at')

    #now that we have the messages it time to build our history
    history = [
        {'role':msg.role , 'content': msg.content} for msg in reversed(messages)
    ]

    redis_client.set(key , json.dumps(history))
    return history

# append new message to history
def append_to_history(session_id, role, content):
    key = HISTORY_KEY.format(session_id)
    cached = redis_client.get(key)
    history = json.loads(cached) if cached else []

    history.append({"role": role, "content": content})

    # Keep only last MAX_HISTORY messages (keep this out for now)
    #if len(history) > MAX_HISTORY:
        #history = history[-MAX_HISTORY:]

    redis_client.set(key, json.dumps(history))

# clear redis cache when session gets invalidated
def invalidate_history(session_id):
    redis_client.delete(HISTORY_KEY.format(session_id))

# celery Task
@shared_task(bind=True , max_retries=3)
def generate_ai_response(self , session_id , room_group_name):
    channel_layer = get_channel_layer()

    try :

        session = InterviewSession.objects.get(id=session_id)
        
        #get history from reddis 
        history = get_history(session_id)

        ai_response = get_ai_response(session, history)

        #save to db
        ai_msg = Message.objects.create(
            session = session,
            role = Message.Role.Assistant,
            content = ai_response
        )

        # push response to websocket
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

        # Notify frontend something went wrong
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                "type": "error",
                "message": "something went wrong please try again."
            }
        )
        raise self.retry(exc=exc, countdown=5)


