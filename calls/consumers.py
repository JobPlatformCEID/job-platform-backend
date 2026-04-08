import json
import logging
from urllib.parse import parse_qs

import redis.asyncio as aioredis
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
import asyncio

from .models import Room
from .livekit_utils import generate_token, LIVEKIT_PUBLIC_URL
from users.models import User

# Redis key helpers

def _room_key(room_id):
    return f"room:{room_id}:users"


def _admitted_key(room_id):
    return f"room:{room_id}:admitted"

_redis_pool: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        host, port = settings.CHANNEL_LAYERS["default"]["CONFIG"]["hosts"][0]
        _redis_pool = aioredis.from_url(
            f"redis://{host}:{port}",
            encoding="utf-8",
            decode_responses=True,
            health_check_interval=30,      # Auto-reconnect stale connections
            socket_connect_timeout=5,      # Fail fast if Redis unreachable
            socket_timeout=5,              # Prevent hanging on slow queries
            retry_on_timeout=True,         # Auto-retry transient timeouts
        )
    return _redis_pool


async def close_redis_pool():
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None

# In-memory store

class InMemoryUserStore:
    def __init__(self):
        # Instance-level dicts prevent cross-instance data leakage
        self._store: dict = {}
        self._admitted: dict = {}
        self._lock = asyncio.Lock()

    async def add_user(self, room_id, user_id, username):
        room_id, user_id = str(room_id), str(user_id)
        async with self._lock:
            if room_id not in self._store:
                self._store[room_id] = {}
            self._store[room_id][user_id] = username

    async def remove_user(self, room_id, user_id):
        room_id, user_id = str(room_id), str(user_id)
        # Atomic cleanup: both _store and _admitted are protected by the SAME lock
        async with self._lock:
            if room_id in self._store:
                self._store[room_id].pop(user_id, None)
                if not self._store[room_id]:
                    del self._store[room_id]
            
            # Clean up admitted in the SAME critical section to keep state consistent
            if room_id in self._admitted:
                self._admitted[room_id].discard(user_id)
                if not self._admitted[room_id]:
                    del self._admitted[room_id]

    async def add_admitted_user(self, room_id, user_id):
        room_id, user_id = str(room_id), str(user_id)
        async with self._lock:
            if room_id not in self._admitted:
                self._admitted[room_id] = set()
            self._admitted[room_id].add(user_id)

    async def remove_admitted_user(self, room_id, user_id):
        room_id, user_id = str(room_id), str(user_id)
        async with self._lock:
            if room_id in self._admitted:
                self._admitted[room_id].discard(user_id)
                if not self._admitted[room_id]:
                    del self._admitted[room_id]

    async def get_users(self, room_id):
        room_id = str(room_id)
        return [
            {"id": int(uid), "username": uname}
            for uid, uname in self._store.get(room_id, {}).items()
        ]

    async def get_waiting_users(self, room_id):
        room_id = str(room_id)
        admitted = self._admitted.get(room_id, set())
        return [
            {"id": int(uid), "username": uname}
            for uid, uname in self._store.get(room_id, {}).items()
            if uid not in admitted
        ]

    async def get_admitted_users(self, room_id):
        room_id = str(room_id)
        admitted = self._admitted.get(room_id, set())
        store_room = self._store.get(room_id, {})
        return [
            {"id": int(uid), "username": store_room.get(uid, "")}
            for uid in admitted
        ]

    async def is_user_admitted(self, room_id, user_id):
        return str(user_id) in self._admitted.get(str(room_id), set())

    def clear(self):
        self._store.clear()
        self._admitted.clear()

# Redis-backed store 

from redis.exceptions import ConnectionError, TimeoutError

logger = logging.getLogger(__name__)

class RedisUserStore:

    async def add_user(self, room_id, user_id, username):
        room_id, user_id = str(room_id), str(user_id)
        try:
            r = get_redis()
            await r.hset(_room_key(room_id), user_id, username)
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Redis add_user failed room={room_id} user={user_id}: {e}")
            raise  # Fail closed: reject the join if Redis is down

    async def remove_user(self, room_id, user_id):
        room_id, user_id = str(room_id), str(user_id)
        try:
            r = get_redis()
            # Remove user from room hash
            await r.hdel(_room_key(room_id), user_id)
            # Remove from admitted set (safe if key/user doesn't exist)
            await r.srem(_admitted_key(room_id), user_id)
            
            # Cleanup: if room is empty, remove admitted set too
            # Small race window exists but consequence is minor:
            # If a new user joins between exists() and unlink(), they'll recreate
            # the admitted set on their first add_admitted_user() call.
            if not await r.exists(_room_key(room_id)):
                await r.unlink(_admitted_key(room_id))  # Non-blocking delete
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Redis remove_user failed room={room_id} user={user_id}: {e}")
            # Don't re-raise: user is leaving anyway; log and continue


    async def add_admitted_user(self, room_id, user_id):
        room_id, user_id = str(room_id), str(user_id)
        try:
            r = get_redis()
            await r.sadd(_admitted_key(room_id), user_id)
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Redis add_admitted_user failed room={room_id} user={user_id}: {e}")
            raise

    async def remove_admitted_user(self, room_id, user_id):
        room_id, user_id = str(room_id), str(user_id)
        try:
            r = get_redis()
            await r.srem(_admitted_key(room_id), user_id)
            # Clean up empty set to avoid key leakage
            if not await r.scard(_admitted_key(room_id)):
                await r.unlink(_admitted_key(room_id))
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Redis remove_admitted_user failed room={room_id} user={user_id}: {e}")
        
    async def get_users(self, room_id):
        room_id=str(room_id)
        try:
            r = get_redis()
            raw = await r.hgetall(_room_key(room_id))
            # decode_responses=True → values are already str, no .decode() needed
            return [
                {'id': int(uid), 'username': uname}
                for uid, uname in raw.items()
            ]
        except (ConnectionError , TimeoutError) as e:
            logger.error(f'redis get_users failed room={room_id}:{e}')
            return [] #empty room to avoid crashing

    async def get_waiting_users(self, room_id):
        room_id = str(room_id)
        try:
            r = get_redis()
            # Pipeline: batch 2 reads into 1 network round-trip
            pipe = r.pipeline()
            pipe.hgetall(_room_key(room_id))
            pipe.smembers(_admitted_key(room_id))
            raw_users, admitted = await pipe.execute()
            
            return [
                {'id': uid, 'username': uname}
                for uid, uname in raw_users.items()
                if uid not in admitted
            ]
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Redis get_waiting_users failed room={room_id}: {e}")
            return []

    async def get_admitted_users(self, room_id):
        room_id = str(room_id)
        try:
            r = get_redis()
            pipe = r.pipeline()
            pipe.hgetall(_room_key(room_id))
            pipe.smembers(_admitted_key(room_id))
            raw_users, admitted = await pipe.execute()
            
            return [
                {'id': uid, 'username': raw_users.get(uid, '')}
                for uid in admitted
            ]
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Redis get_admitted_users failed room={room_id}: {e}")
            return []

    async def is_user_admitted(self, room_id, user_id):
        room_id, user_id = str(room_id), str(user_id)
        try:
            r = get_redis()
            return await r.sismember(_admitted_key(room_id), user_id)
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Redis is_user_admitted failed room={room_id} user={user_id}: {e}")
            return False

_store_instance: InMemoryUserStore | None = None


def _get_user_store():
    # Production default: always use Redis
    # Memory store is ONLY for single-process dev/testing
    if getattr(settings, 'CALL_USER_STORE', 'redis') == 'memory':
        if not getattr(settings, 'DEBUG', False):
            logger.critical(
                "InMemoryUserStore used outside DEBUG mode. "
                "This will break with multiple workers. Set CALL_USER_STORE='redis' for production."
            )
        global _store_instance
        if _store_instance is None:
            _store_instance = InMemoryUserStore()
        return _store_instance
    return RedisUserStore()

# Base consumer

class RoomConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        await self.accept()
        self._joined = False
        self._store = _get_user_store()

        try:
            self.user = self.scope.get('user')

            if not self.user or not self.user.is_authenticated:
                query_string = self.scope.get('query_string', b'').decode()
                params = parse_qs(query_string)
                token_key = params.get('token', [None])[0]

                if not token_key:
                    await self.close(code=4001)
                    return

                self.user = await self.get_user_from_token(token_key)
                if self.user is None:
                    await self.close(code=4001)
                    return

            self.username = self.user.username
            self.room_id = self.scope['url_route']['kwargs']['room_id']
            self.room = await self.get_room()
            self.room_group_name = f"calls_{self.room_id}"

            # Debug timezone comparison
            logging.error(f"NOW: {timezone.now()} | MEETING: {self.room.meeting_date} | BEFORE: {timezone.now() < self.room.meeting_date}")

            if timezone.now() < self.room.meeting_date:
                await self.close(
                    code=4003,
                    reason=f"Meeting has already passed. Scheduled for: {self.room.meeting_date}"
                )
                return

            if not self.room.is_active:
                await self.set_room_active(True)
                self.room.is_active = True

            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.channel_layer.group_add(f"user_{self.username}", self.channel_name)
            await self._store.add_user(self.room_id, self.user.id, self.username)

            is_host = self.user.id == self.room.host_id

            # Host is NOT admitted immediately - only when they press "Start Call"
            # This allows guests to see waiting state until host actually joins

            self._joined = True

            users = await self._store.get_users(self.room_id)
            waiting_users = await self._store.get_waiting_users(self.room_id)

            host_present = await self._store.is_user_admitted(self.room_id, self.room.host_id)
            await self.send(text_data=json.dumps({
                'type': 'room_state',
                'host_present': host_present,
                'waiting_users': [u['username'] for u in waiting_users],
                'users': [u['username'] for u in users],
            }))

            if is_host:
                # Don't send call_started here - host will send it when they press Start Call
                pass

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_joined',
                    'username': self.username,
                    'users': users,
                    'waiting_users': [u['username'] for u in waiting_users],
                },
            )

        except Exception as e:
            logging.error(f"WebSocket connection error: {e}")
            await self.close(code=4000)

    async def disconnect(self, code):
        if not hasattr(self, 'room_group_name') or not self._joined:
            return

        await self._store.remove_user(self.room_id, self.user.id)

        users = await self._store.get_users(self.room_id)
        waiting_users = await self._store.get_waiting_users(self.room_id)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'username': self.username,
                'users': users,
                'waiting_users': [u['username'] for u in waiting_users],
            },
        )

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        await self.channel_layer.group_discard(f"user_{self.username}", self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        if data.get('type') == 'kick':
            await self.kick_user_by_id(data.get('user_id'))

    async def kick_user_by_id(self, user_id):
        if self.user.id != self.room.host_id:
            logging.warning(f"Non-host {self.username} tried to kick user_id={user_id}")
            return
        try:
            target = await database_sync_to_async(User.objects.get)(id=user_id)
        except User.DoesNotExist:
            logging.warning(f"kick_user_by_id: user {user_id} not found")
            return
        await self.channel_layer.group_send(
            f"user_{target.username}",
            {'type': 'kicked'},
        )

    @database_sync_to_async
    def get_user_from_token(self, token_key):
        try:
            return Token.objects.get(key=token_key).user
        except Token.DoesNotExist:
            return None

    @database_sync_to_async
    def get_room(self):
        return Room.objects.get(id=self.room_id)

    @database_sync_to_async
    def set_room_active(self, state):
        Room.objects.filter(id=self.room_id).update(is_active=state)

    # Channel-layer event handlers

    async def call_started(self, event):
        await self.send(text_data=json.dumps({'type': 'call_started'}))

    async def user_joined(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_joined',
            'username': event['username'],
            'users': event.get('users', []),
            'waiting_users': event.get('waiting_users', []),
        }))

    async def user_left(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'username': event['username'],
            'users': event.get('users', []),
            'waiting_users': event.get('waiting_users', []),
        }))



# Video calls consumer
class VideoCalls(RoomConsumer):

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('type')

        if action == 'kick':
            await self.kick_user_by_id(data.get('user_id'))
        elif action == 'kick_user':
            await self.kick_user(data['username'])
        elif action == 'admit_guest':
            await self.admit_user(data.get('username'))
        elif action == 'notify_host':
            await self.notify_host(data.get('message'))
        elif action == 'call_started':
            # Host is starting the call, admit them and broadcast to all guests
            if self.user.id == self.room.host_id:
                # Mark host as admitted
                await self._store.add_admitted_user(self.room_id, self.user.id)
                # Notify all guests that host has joined
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {'type': 'call_started'},
                )
                # Update waiting list for all
                waiting_users = await self._store.get_waiting_users(self.room_id)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'waiting_users_updated',
                        'waiting_users': [u['username'] for u in waiting_users],
                    }
                )

    async def admit_user(self, username):
        if self.user.id != self.room.host_id:
            logging.warning(f"Non-host {self.username} tried to admit {username}")
            return

        try:
            user_obj = await database_sync_to_async(User.objects.get)(username=username)
        except User.DoesNotExist:
            logging.warning(f"admit_user: user '{username}' not found")
            return

        token = generate_token(self.room.room_name, user_obj.username, is_host=False)
        await self._store.add_admitted_user(self.room_id, user_obj.id)

        await self.channel_layer.group_send(
            f"user_{user_obj.username}",
            {
                'type': 'admitted',
                'livekit_url': LIVEKIT_PUBLIC_URL,
                'livekit_token': token,
                'host_username': self.username,
            }
        )

        waiting_users = await self._store.get_waiting_users(self.room_id)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'waiting_users_updated',
                'waiting_users': [u['username'] for u in waiting_users],
            }
        )

        logging.info(f"Host {self.username} admitted {username} to room {self.room_id}")

    async def kick_user(self, username):
        if self.user.id != self.room.host_id:
            logging.warning(f"Non-host {self.username} tried to kick {username}")
            return

        await self.channel_layer.group_send(
            f"user_{username}",
            {'type': 'kicked'},
        )
        logging.info(f"Host {self.username} kicked {username} from room {self.room_id}")

    async def notify_host(self, message):
        try:
            host_user = await database_sync_to_async(User.objects.get)(id=self.room.host_id)
        except User.DoesNotExist:
            logger.error(f"Host user {self.room.host_id} not found for room {self.room_id}")
            return

        host_username = host_user.username

        await self.channel_layer.group_send(
            f"user_{host_username}",
            {
                'type': 'host_notification',
                'message': message,
                'from_user': self.username,
            }
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_wants_to_join',
                'message': message,
                'from_user': self.username,
            }
        )

        logging.info(f"Notification sent to host {host_username} from {self.username}")

    # Channel-layer event handlers

    async def admitted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'admitted',
            'livekit_url': event.get('livekit_url'),
            'livekit_token': event.get('livekit_token'),
            'host_username': event.get('host_username'),
        }))

    async def kicked(self, event):
        await self.send(text_data=json.dumps({'type': 'kicked'}))

    async def waiting_users_updated(self, event):
        await self.send(text_data=json.dumps({
            'type': 'waiting_users_updated',
            'waiting_users': event.get('waiting_users', []),
        }))

    async def host_notification(self, event):
        await self.send(text_data=json.dumps({
            'type': 'host_notification',
            'message': event.get('message', ''),
            'from_user': event.get('from_user', ''),
        }))

    async def user_wants_to_join(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_wants_to_join',
            'message': event.get('message', ''),
            'from_user': event.get('from_user', ''),
        }))
  

# Messaging consumer 
class Messaging(RoomConsumer):

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('type')

        if action == 'kick':
            await self.kick_user_by_id(data.get('user_id'))

        elif action == 'message':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'sender': self.username,
                    'message': data.get('message', ''),
                },
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'sender': event['sender'],
            'message': event['message'],
        }))