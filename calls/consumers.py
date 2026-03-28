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
    return f"room:{room_id}:users"


async def _get_redis():
    redis_url = settings.CHANNEL_LAYERS["default"]["CONFIG"]["hosts"][0]
    host, port = redis_url
    return await aioredis.from_url(f"redis://{host}:{port}")


class RoomConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        await self.accept()

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
                await self.close(code=4003)
                return

            if not self.room.is_active and self.user.id != self.room.host_id:
                await self.close(code=4004)
                return

            if not self.room.is_active and self.user.id == self.room.host_id:
                await self.set_room_active(True)
                self.room.is_active = True

            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.add_user()

            users = await self.get_users()
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'user_joined', 'username': self.username, 'users': users},
            )

        except Exception as e:
            logging.error(f"WebSocket connection error: {e}")
            await self.close(code=4000)

    async def disconnect(self, code):
        if not hasattr(self, 'room_group_name'):
            return

        await self.remove_user()
        users = await self.get_users()

        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'user_left', 'username': self.username, 'users': users},
        )

        if self.user.id == self.room.host_id:
            await self.set_room_active(False)

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        if data.get('type') == 'kick':
            await self.kick(data.get('user_id'))

    async def add_user(self):
        r = await _get_redis()
        await r.hset(_room_key(self.room_id), self.user.id, self.username)
        await r.aclose()

    async def remove_user(self):
        r = await _get_redis()
        await r.hdel(_room_key(self.room_id), self.user.id)
        await r.aclose()

    async def get_users(self):
        r = await _get_redis()
        raw = await r.hgetall(_room_key(self.room_id))
        await r.aclose()
        return [
            {'id': int(uid), 'username': uname.decode()}
            for uid, uname in raw.items()
        ]

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
class Messaging(RoomConsumer):
    pass