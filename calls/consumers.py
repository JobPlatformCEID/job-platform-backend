import json
import logging
from urllib.parse import parse_qs

import redis.asyncio as aioredis
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings
from django.utils import timezone
from rest_framework.authtoken.models import Token

from .models import Room


def _room_key(room_id):
    return f"room:{room_id}:active_users"

def _waiting_key(room_id):
    return f"room:{room_id}:waiting_users"

def _call_started_key(room_id):
    return f"room:{room_id}:call_started"

def _admitted_key(room_id):
    return f"room:{room_id}:admitted_users"


# ─────────────────────────────────────────────────────────────────────────────
# In-memory store
# ─────────────────────────────────────────────────────────────────────────────
class InMemoryUserStore:
    # FIX: Move class variables to instance variables in __init__
    def __init__(self):
        self._active:       dict = {}
        self._waiting:      dict = {}
        self._admitted:     dict = {}
        self._call_started: dict = {}

    async def add_active_user(self, room_id, user_id, username):
        rid, uid = str(room_id), str(user_id)
        self._waiting.setdefault(rid, {}).pop(uid, None)
        self._active.setdefault(rid, {})[uid] = username

    async def add_waiting_user(self, room_id, user_id, username):
        rid, uid = str(room_id), str(user_id)
        self._active.setdefault(rid, {}).pop(uid, None)
        self._waiting.setdefault(rid, {})[uid] = username

    async def admit_user(self, room_id, user_id):
        rid, uid = str(room_id), str(user_id)
        username = self._waiting.get(rid, {}).pop(uid, None)
        if username:
            self._active.setdefault(rid, {})[uid] = username
            self._admitted.setdefault(rid, set()).add(uid)
        return username

    async def is_admitted(self, room_id, user_id):
        return str(user_id) in self._admitted.get(str(room_id), set())

    async def remove_user(self, room_id, user_id):
        rid, uid = str(room_id), str(user_id)
        self._active.get(rid, {}).pop(uid, None)
        self._waiting.get(rid, {}).pop(uid, None)
        self._admitted.get(rid, set()).discard(uid)

    async def clear_room(self, room_id):
        rid = str(room_id)
        self._active.pop(rid, None)
        self._waiting.pop(rid, None)
        self._call_started.pop(rid, None)
        self._admitted.pop(rid, None)

    async def get_active_users(self, room_id):
        return [{'id': int(uid), 'username': uname} for uid, uname in self._active.get(str(room_id), {}).items()]

    async def get_waiting_users(self, room_id):
        return [{'id': int(uid), 'username': uname} for uid, uname in self._waiting.get(str(room_id), {}).items()]

    async def set_call_started(self, room_id, value: bool):
        self._call_started[str(room_id)] = value

    async def get_call_started(self, room_id):
        return self._call_started.get(str(room_id), False)

    # FIX: Removed clear() classmethod since variables are now instance-level


# ─────────────────────────────────────────────────────────────────────────────
# Redis store
# ─────────────────────────────────────────────────────────────────────────────
class RedisUserStore:
    _redis_pool = None
    
    async def _get_redis(self):
        # FIX: Use type(self)._redis_pool for class-level pooling
        # FIX: Add max_connections and health_check_interval
        if type(self)._redis_pool is None:
            host, port = settings.CHANNEL_LAYERS["default"]["CONFIG"]["hosts"][0]
            type(self)._redis_pool = await aioredis.from_url(
                f"redis://{host}:{port}",
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,
                health_check_interval=30
            )
        return type(self)._redis_pool

    async def add_active_user(self, room_id, user_id, username):
        try:
            r = await self._get_redis()
            await r.hdel(_waiting_key(room_id), user_id)
            await r.hset(_room_key(room_id), user_id, username)
        except aioredis.ConnectionError as e:
            logging.warning(f'Redis connection error in add_active_user: {e}')

    async def add_waiting_user(self, room_id, user_id, username):
        try:
            r = await self._get_redis()
            await r.hdel(_room_key(room_id), user_id)
            await r.hset(_waiting_key(room_id), user_id, username)
        except aioredis.ConnectionError as e:
            logging.warning(f'Redis connection error in add_waiting_user: {e}')

    async def admit_user(self, room_id, user_id):
        try:
            r = await self._get_redis()
            raw = await r.hget(_waiting_key(room_id), user_id)
            if raw:
                username = raw
                await r.hdel(_waiting_key(room_id), user_id)
                await r.hset(_room_key(room_id), user_id, username)
                await r.sadd(_admitted_key(room_id), user_id)
                return username
            return None
        except aioredis.ConnectionError as e:
            logging.warning(f'Redis connection error in admit_user: {e}')
            return None

    async def is_admitted(self, room_id, user_id):
        try:
            r = await self._get_redis()
            val = await r.sismember(_admitted_key(room_id), str(user_id))
            return val
        except aioredis.ConnectionError as e:
            logging.warning(f'Redis connection error in is_admitted: {e}')
            return False

    async def remove_user(self, room_id, user_id):
        try:
            r = await self._get_redis()
            await r.hdel(_room_key(room_id), user_id)
            await r.hdel(_waiting_key(room_id), user_id)
            await r.srem(_admitted_key(room_id), user_id)
        except aioredis.ConnectionError as e:
            logging.warning(f'Redis connection error in remove_user: {e}')

    async def clear_room(self, room_id):
        try:
            r = await self._get_redis()
            await r.delete(_room_key(room_id), _waiting_key(room_id), _call_started_key(room_id), _admitted_key(room_id))
        except aioredis.ConnectionError as e:
            logging.warning(f'Redis connection error in clear_room: {e}')

    async def get_active_users(self, room_id):
        try:
            r = await self._get_redis()
            data = await r.hgetall(_room_key(room_id))
            return [{'id': int(k), 'username': v} for k, v in data.items()]
        except aioredis.ConnectionError as e:
            logging.warning(f'Redis connection error in get_active_users: {e}')
            return []

    async def get_waiting_users(self, room_id):
        try:
            r = await self._get_redis()
            data = await r.hgetall(_waiting_key(room_id))
            return [{'id': int(k), 'username': v} for k, v in data.items()]
        except aioredis.ConnectionError as e:
            logging.warning(f'Redis connection error in get_waiting_users: {e}')
            return []

    async def set_call_started(self, room_id, value: bool):
        try:
            r = await self._get_redis()
            await r.set(_call_started_key(room_id), '1' if value else '0')
        except aioredis.ConnectionError as e:
            logging.warning(f'Redis connection error in set_call_started: {e}')

    async def get_call_started(self, room_id):
        try:
            r = await self._get_redis()
            val = await r.get(_call_started_key(room_id))
            return val == '1'
        except aioredis.ConnectionError as e:
            logging.warning(f'Redis connection error in get_call_started: {e}')
            return False


def _get_user_store():
    if getattr(settings, 'CALL_USER_STORE', 'redis') == 'memory':
        return InMemoryUserStore()
    return RedisUserStore()


# ─────────────────────────────────────────────────────────────────────────────
# Base consumer
# ─────────────────────────────────────────────────────────────────────────────
class RoomConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        await self.accept()
        self._joined = False
        self._store  = _get_user_store()

        try:
            self.user = self.scope.get('user')

            if not self.user or not self.user.is_authenticated:
                qs = self.scope.get('query_string', b'').decode()
                token_key = parse_qs(qs).get('token', [None])[0]
                if not token_key:
                    await self.close(code=4001); return
                self.user = await self.get_user_from_token(token_key)
                if self.user is None:
                    await self.close(code=4001); return

            self.username        = self.user.username
            self.room_id         = self.scope['url_route']['kwargs']['room_id']
            self.room            = await self.get_room()
            self.room_group_name = f"calls_{self.room_id}"

            if timezone.now() < self.room.meeting_date:
                await self.close(code=4003); return

            # Connect logic: Persist admission state even if they drop connection briefly
            is_admitted_guest = await self._store.is_admitted(self.room_id, self.user.id)
            if self.user.id == self.room.host_id or is_admitted_guest:
                if self.user.id == self.room.host_id and not self.room.is_active:
                    await self.set_room_active(True)
                    self.room.is_active = True
                await self._store.add_active_user(self.room_id, self.user.id, self.username)
            else:
                await self._store.add_waiting_user(self.room_id, self.user.id, self.username)

            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            self._joined = True

            active_users  = await self._store.get_active_users(self.room_id)
            waiting_users = await self._store.get_waiting_users(self.room_id)
            call_started  = await self._store.get_call_started(self.room_id)

            await self.send(text_data=json.dumps({
                'type':          'room_status',
                'is_active':     self.room.is_active,
                'call_started':  call_started,
                'users':         active_users,
                'waiting_users': waiting_users,
            }))

            await self.channel_layer.group_send(self.room_group_name, {
                'type':          'user_joined_handler',
                'username':      self.username,
                'users':         active_users,
                'waiting_users': waiting_users,
            })

        except Exception as e:
            logging.error(f"WebSocket connect error: {e}")
            await self.close(code=4000)

    async def disconnect(self, code):
        if not hasattr(self, 'room_group_name') or not self._joined:
            return

        await self._store.remove_user(self.room_id, self.user.id)
        active_users  = await self._store.get_active_users(self.room_id)
        waiting_users = await self._store.get_waiting_users(self.room_id)

        # Notify others they left, but DO NOT violently clear the room on normal drops.
        # It handles host navigation cleanly now.
        await self.channel_layer.group_send(self.room_group_name, {
            'type':          'user_left_handler',
            'username':      self.username,
            'users':         active_users,
            'waiting_users': waiting_users,
        })

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        if data.get('type') == 'kick':
            await self.kick(data.get('user_id'))

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

    async def kick(self, user_id):
        if self.user.id != self.room.host_id:
            return
        await self.channel_layer.group_send(self.room_group_name,
            {'type': 'kicked_handler', 'user_id': user_id})

    async def user_joined_handler(self, event):
        await self.send(text_data=json.dumps({
            'type':          'user_joined',
            'username':      event['username'],
            'users':         event['users'],
            'waiting_users': event['waiting_users'],
        }))

    async def user_left_handler(self, event):
        await self.send(text_data=json.dumps({
            'type':          'user_left',
            'username':      event['username'],
            'users':         event['users'],
            'waiting_users': event['waiting_users'],
        }))

    async def room_status_update(self, event):
        await self.send(text_data=json.dumps({
            'type':          'room_status',
            'is_active':     event['is_active'],
            'users':         event.get('users', []),
            'waiting_users': event.get('waiting_users', []),
        }))

    async def kicked_handler(self, event):
        if self.user.id == event['user_id']:
            await self.close(code=4003)


# ─────────────────────────────────────────────────────────────────────────────
# VideoCalls consumer
# ─────────────────────────────────────────────────────────────────────────────
class VideoCalls(RoomConsumer):

    async def receive(self, text_data):
        data   = json.loads(text_data)
        action = data.get('type')

        if action == 'kick':
            await self.kick(data.get('user_id'))

        elif action == 'call_started':
            if self.user.id == self.room.host_id:
                await self._store.set_call_started(self.room_id, True)
                await self.channel_layer.group_send(self.room_group_name,
                    {'type': 'call_started_handler', 'host': self.username})

        elif action == 'notify_host':
            await self.channel_layer.group_send(self.room_group_name, {
                'type':    'notify_host_message',
                'sender':  self.username,
                'message': data.get('message', f'{self.username} is waiting to join.'),
                'host_id': self.room.host_id,
            })
            
        elif action == 'end_call':
            if self.user.id == self.room.host_id:
                await self.set_room_active(False)
                await self._store.clear_room(self.room_id)
                await self.channel_layer.group_send(self.room_group_name, {
                    'type':          'room_status_update',
                    'is_active':     False,
                    'users':         [],
                    'waiting_users': [],
                })

        elif action == 'admit_guest':
            if self.user.id != self.room.host_id:
                return
            target_username = data.get('username')
            if not target_username:
                return

            waiting = await self._store.get_waiting_users(self.room_id)
            target_id = next((u['id'] for u in waiting if u['username'] == target_username), None)
            if target_id is None:
                return

            admitted_username = await self._store.admit_user(self.room_id, target_id)
            if not admitted_username:
                return

            active_users  = await self._store.get_active_users(self.room_id)
            waiting_users = await self._store.get_waiting_users(self.room_id)

            await self.channel_layer.group_send(self.room_group_name, {
                'type':            'admitted_handler',
                'target_username': target_username,
                'host_username':   self.username,
                'users':           active_users,
                'waiting_users':   waiting_users,
                'initiator':       self.username,  # FIX 1: Host always initiates offer to newly admitted guest
            })

            await self.channel_layer.group_send(self.room_group_name, {
                'type':          'user_admitted_handler',
                'username':      target_username,
                'users':         active_users,
                'waiting_users': waiting_users,
                'host_username': self.username,  # FIX 1: Add host_username for initiator field
            })

        elif action == 'offer':
            await self.channel_layer.group_send(self.room_group_name, {
                'type':   'webrtc_offer',
                'offer':  data['offer'],
                'sender': self.username,
                'target': data.get('target'),
            })

        elif action == 'answer':
            await self.channel_layer.group_send(self.room_group_name, {
                'type':   'webrtc_answer',
                'answer': data['answer'],
                'sender': self.username,
                'target': data.get('target'),
            })

        elif action == 'ice_candidate':
            await self.channel_layer.group_send(self.room_group_name, {
                'type':      'webrtc_ice',
                'candidate': data['candidate'],
                'sender':    self.username,
                'target':    data.get('target'),
            })

        elif action == 'message':
            await self.channel_layer.group_send(self.room_group_name, {
                'type':    'chat_message',
                'sender':  self.username,
                'message': data.get('message', ''),
            })

    async def webrtc_offer(self, event):
        if event.get('target') == self.username:
            await self.send(text_data=json.dumps({'type': 'offer', 'offer': event['offer'], 'sender': event['sender']}))

    async def webrtc_answer(self, event):
        if event.get('target') == self.username:
            await self.send(text_data=json.dumps({'type': 'answer', 'answer': event['answer'], 'sender': event['sender']}))

    async def webrtc_ice(self, event):
        if event.get('target') == self.username:
            await self.send(text_data=json.dumps({'type': 'ice_candidate', 'candidate': event['candidate'], 'sender': event['sender']}))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({'type': 'message', 'sender': event['sender'], 'message': event['message']}))

    async def call_started_handler(self, event):
        await self.send(text_data=json.dumps({'type': 'call_started', 'host': event['host']}))

    async def notify_host_message(self, event):
        if self.user.id == event['host_id']:
            await self.send(text_data=json.dumps({'type': 'message', 'sender': event['sender'], 'message': event['message']}))

    async def admitted_handler(self, event):
        if self.username == event['target_username']:
            await self.send(text_data=json.dumps({
                'type':          'admitted',
                'host_username': event['host_username'],
                'users':         event.get('users', []),
                'waiting_users': event.get('waiting_users', []),
                'initiator':     event['host_username'],  # FIX 1: Host always initiates offer to newly admitted guest
            }))

    async def user_admitted_handler(self, event):
        await self.send(text_data=json.dumps({
            'type':          'user_admitted',
            'username':      event['username'],
            'users':         event['users'],
            'waiting_users': event['waiting_users'],
            'initiator':     event.get('host_username', event.get('users', [{}])[0].get('username')),  # FIX 1: Host always initiates offer
        }))

class Messaging(RoomConsumer):
    async def receive(self, text_data):
        data = json.loads(text_data)
        if data.get('type') == 'kick':
            await self.kick(data.get('user_id'))
        elif data.get('type') == 'message':
            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'chat_message', 'sender': self.username, 'message': data.get('message', '')
            })

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({'type': 'message', 'sender': event['sender'], 'message': event['message']}))