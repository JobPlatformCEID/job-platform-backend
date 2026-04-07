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
from .livekit_utils import generate_token, LIVEKIT_PUBLIC_URL


def _room_key(room_id):
    return f"room:{room_id}:users"


class InMemoryUserStore:
    _store: dict = {}

    async def add_user(self, room_id, user_id, username):
        room_id = str(room_id)
        if room_id not in self._store:
            self._store[room_id] = {}
        self._store[room_id][str(user_id)] = username

    async def remove_user(self, room_id, user_id):
        room_id = str(room_id)
        if room_id in self._store:
            self._store[room_id].pop(str(user_id), None)
            if not self._store[room_id]:
                del self._store[room_id]

    async def get_users(self, room_id):
        return [
            {'id': int(uid), 'username': uname}
            for uid, uname in self._store.get(str(room_id), {}).items()
        ]

    @classmethod
    def clear(cls):
        cls._store.clear()


class RedisUserStore:
    async def _redis(self):
        host, port = settings.CHANNEL_LAYERS["default"]["CONFIG"]["hosts"][0]
        return await aioredis.from_url(f"redis://{host}:{port}")

    async def add_user(self, room_id, user_id, username):
        r = await self._redis()
        await r.hset(_room_key(room_id), user_id, username)
        await r.aclose()

    async def remove_user(self, room_id, user_id):
        r = await self._redis()
        await r.hdel(_room_key(room_id), user_id)
        await r.aclose()

    async def get_users(self, room_id):
        r = await self._redis()
        raw = await r.hgetall(_room_key(room_id))
        await r.aclose()
        return [
            {'id': int(uid), 'username': uname.decode()}
            for uid, uname in raw.items()
        ]


def _get_user_store():
    if getattr(settings, 'CALL_USER_STORE', 'redis') == 'memory':
        return InMemoryUserStore()
    return RedisUserStore()


class RoomConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        await self.accept()
        self._joined = False
        self._store  = _get_user_store()

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

            self.username        = self.user.username
            self.room_id         = self.scope['url_route']['kwargs']['room_id']
            self.room            = await self.get_room()
            self.room_group_name = f"calls_{self.room_id}"

            if timezone.now() < self.room.meeting_date:
                await self.close(code=4003, reason=f"Meeting has not started yet. Scheduled for: {self.room.meeting_date}")
                return

            # Room is active if meeting time has arrived
            if not self.room.is_active:
                await self.set_room_active(True)
                self.room.is_active = True

            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.channel_layer.group_add(f"user_{self.username}", self.channel_name)
            await self._store.add_user(self.room_id, self.user.id, self.username)
            self._joined = True

            users = await self._store.get_users(self.room_id)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_joined',
                    'username': self.username,
                    'users': users,
                    'waiting_users': users,
                    'call_started': True,
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

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'username': self.username,
                'users': users,
                'waiting_users': users,
                'call_started': True,
            },
        )

        # Room stays active based on meeting time, not host presence

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        await self.channel_layer.group_discard(f"user_{self.username}", self.channel_name)

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

    async def user_joined(self, event):
        await self.send(text_data=json.dumps({
            'type':     'user_joined',
            'username': event['username'],
            'users':    event.get('users', []),
        }))

    async def user_left(self, event):
        await self.send(text_data=json.dumps({
            'type':     'user_left',
            'username': event['username'],
            'users':    event.get('users', []),
        }))

    async def kicked_handler(self, event):
        if self.user.id == event['user_id']:
            await self.close(code=4003)

    async def kick(self, user_id):
        if self.user.id != self.room.host_id:
            await self.close(code=4003)
            return
        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'kicked_handler', 'user_id': user_id},
        )


class VideoCalls(RoomConsumer):

    async def receive(self, text_data):
        data   = json.loads(text_data)
        action = data.get('type')

        if action == 'kick':
            await self.kick(data.get('user_id'))

        elif action == 'kick_user':
            await self.kick_user(data['username'], self.scope['user'].username)

        elif action == 'admit_guest':
            await self.admit_user(data.get('username'))

        elif action == 'offer':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type':   'webrtc_offer',
                    'offer':  data['offer'],
                    'sender': self.username,
                    'target': data.get('target'),
                },
            )

        elif action == 'answer':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type':   'webrtc_answer',
                    'answer': data['answer'],
                    'sender': self.username,
                    'target': data.get('target'),
                },
            )

        elif action == 'ice_candidate':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type':      'webrtc_ice',
                    'candidate': data['candidate'],
                    'sender':    self.username,
                    'target':    data.get('target'),
                },
            )

    async def webrtc_offer(self, event):
        if event.get('target') == self.username:
            await self.send(text_data=json.dumps({
                'type':   'offer',
                'offer':  event['offer'],
                'sender': event['sender'],
            }))

    async def webrtc_answer(self, event):
        if event.get('target') == self.username:
            await self.send(text_data=json.dumps({
                'type':   'answer',
                'answer': event['answer'],
                'sender': event['sender'],
            }))

    async def webrtc_ice(self, event):
        if event.get('target') == self.username:
            await self.send(text_data=json.dumps({
                'type':      'ice_candidate',
                'candidate': event['candidate'],
                'sender':    event['sender'],
            }))

    async def admit_user(self, username):
        if self.user.id != self.room.host_id:
            logging.warning(f"Non-host {self.username} tried to admit {username}")
            return
        
        token = generate_token(self.room.room_name, username, is_host=False)
        
        # Send to the admitted user's channel
        await self.channel_layer.group_send(
            f"user_{username}",
            {
                "type": "admitted",
                "livekit_url": LIVEKIT_PUBLIC_URL,
                "livekit_token": token,
                "host_username": self.username,
            }
        )
        
        logging.info(f"Host {self.username} admitted {username} to room {self.room_id}")

    async def kick_user(self, username, initiator):
        if self.user.id != self.room.host_id:
            logging.warning(f"Non-host {initiator} tried to kick {username}")
            return
        
        # Send kick message to the user
        await self.channel_layer.group_send(
            f"user_{username}",
            {
                "type": "kicked",
            }
        )
        
        logging.info(f"Host {initiator} kicked {username} from room {self.room_id}")

    async def admitted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'admitted',
            'livekit_url': event.get('livekit_url'),
            'livekit_token': event.get('livekit_token'),
            'host_username': event.get('host_username'),
        }))

    async def kicked(self, event):
        await self.send(text_data=json.dumps({
            'type': 'kicked',
        }))


class Messaging(RoomConsumer):

    async def receive(self, text_data):
        data   = json.loads(text_data)
        action = data.get('type')

        if action == 'kick':
            await self.kick(data.get('user_id'))

        elif action == 'message':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type':    'chat_message',
                    'sender':  self.username,
                    'message': data.get('message', ''),
                },
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type':    'message',
            'sender':  event['sender'],
            'message': event['message'],
        }))
