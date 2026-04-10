import json
import logging
import asyncio

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from .models import InterviewSession, Message
from .tasks import generate_ai_response, append_to_history

logger = logging.getLogger(__name__)


class InterviewConsumer(AsyncWebsocketConsumer):

    #  Connection lifecycle
    async def connect(self):

        self.session_id = self.scope["url_route"]["kwargs"]["session_id"]

        session = await self.get_session()

        if session is None:
            logger.error(f'session {self.session_id} doesnt exist')
            await self.close(code=4404) # not found
            return
        
        #verify the user
        user = self.scope.get('user')
        if not user or user != session.user:
            logger.error(f'session {self.session_id} doesnt belong to {user}')
            await self.close(code=4403) # session belongs to someone else
            return

        self.room_group_name = f"interview_session_{self.session_id}"

        # Reject the connection if the session doesn't exist
        session = await self.get_session()
        if session is None:
            logger.warning(f"Connection refused: session {self.session_id} not found")
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        logger.info(f"WebSocket connected: session={self.session_id}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        logger.info(f"WebSocket disconnected: session={self.session_id}, code={close_code}")

    #  Incoming message
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            content = data.get("content", "").strip()
        except (json.JSONDecodeError, AttributeError):
            await self.send_error("Invalid message format.")
            return

        if not content:
            await self.send_error("Message content cannot be empty.")
            return

        # Persist the user message to PostgreSQL
        user_msg = await self.save_message(role=Message.Role.User, content=content)

        # Append to Redis so Celery picks it up immediately
        # Await Redis write — event loop stays free, and we confirm before firing Celery
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, append_to_history, self.session_id, "user", content)
        except Exception as e:
            logger.error(f"Redis append failed: {e}")
            await self.send_error("Failed to process message, please try again.")
            return  # Don't fire Celery with stale history

        # Echo the user message back to this socket
        # (so the frontend can render it as server-confirmed)
        await self.send(text_data=json.dumps({
            "type": "user_message",
            "message": {
                "id": user_msg.id,
                "role": user_msg.role,
                "content": user_msg.content,
                "created_at": user_msg.created_at.isoformat(),
            }
        }))

        # Fire Celery — it reads history from Redis, calls AI,
        # saves the response, and pushes it back via group_send
        generate_ai_response.delay(self.session_id, self.room_group_name)

    #  Handlers for messages pushed from Celery via channel layer
    async def ai_message(self, event):
        
        await self.send(text_data=json.dumps({
            "type": "ai_message",
            "message": event["message"],
        }))

    async def error(self, event):
        await self.send(text_data=json.dumps({
            "type": "error",
            "message": event["message"],
        }))

    #  Helpers
    @database_sync_to_async
    def get_session(self):
        try:
            return InterviewSession.objects.get(id=self.session_id)
        except InterviewSession.DoesNotExist:
            return None

    @database_sync_to_async
    def save_message(self, role, content):
        session = InterviewSession.objects.get(id=self.session_id)
        return Message.objects.create(session=session, role=role, content=content)

    async def send_error(self, message: str):
        await self.send(text_data=json.dumps({
            "type": "error",
            "message": message,
        }))