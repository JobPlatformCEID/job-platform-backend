from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Room
import redis.asyncio as redis
import json
import logging
import os


class RoomConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        # Immediate Handshake
        await self.accept()

        # Initialise redis as None
        self.redis=None

        try:
            # Authenticity Check
            if self.scope['user'].is_anonymous:
                await self.close(code=4001)
                return

            self.room_id = self.scope['url_route']['kwargs']['room_id']
            self.user = self.scope["user"]
            self.username = self.user.username
            
            redis_host = os.getenv("REDIS_HOST", "redis")
            self.redis = redis.Redis(host="redis", port=6379, decode_responses=True)
            self.room = await self.get_room()
            self.room_group_name = f"calls_{self.room_id}"
            self.redis_key = f"room:{self.room_id}:users"

            # time Validation
            if timezone.now() < self.room.meeting_date:
                await self.close(code=4003)
                return

            # host Activation
            if self.user.id == self.room.host_id:
                await self.set_room_active(True)
                self.room.is_active = True

            # permission Check (Block candidate if room is not active)
            if not self.room.is_active and self.user.id != self.room.host_id:
                await self.close(code=4004)
                return

            # finalize connection
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.add_user_to_room()

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_joined',
                    'username': self.username,
                    'users': await self.get_room_users(),
                },
            )
        except Exception as e:
            logging.error(f"WebSocket Connection Error: {e}")
            await self.close(code=4000)
    
    async def receive(self, text_data):
        data = json.loads(text_data)

        action = data.get('type')

        if action == 'kick':
            await self.kick(data.get('user_id'))


    async def disconnect(self, code):
        if not hasattr(self, 'room_group_name'):
            return

        # update redis
        await self.remove_user_from_room()

        #get the new user list
        updated_users = await self.get_room_users()

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'username': self.username,
                'users': await self.get_room_users(),
            },
        )


        if self.user.id == self.room.host_id:
            await self.set_room_active(False)

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        await self.redis.close()

    # Redis user management

    async def get_room_users(self):
        users = await self.redis.get(self.redis_key)
        return json.loads(users) if users else []

    async def add_user_to_room(self):
        users = await self.get_room_users()

        if not any(u['id'] == self.user.id for u in users):
            users.append({'id': self.user.id, 'username': self.username})

        await self.redis.set(self.redis_key, json.dumps(users))

    async def remove_user_from_room(self):
        users = await self.get_room_users()
        users = [u for u in users if u['id'] != self.user.id]

        await self.redis.set(self.redis_key, json.dumps(users))

    
    # DB operations
    
    @database_sync_to_async
    def get_room(self):
        return Room.objects.get(id=self.room_id)

    @database_sync_to_async
    def set_room_active(self, state):
        Room.objects.filter(id=self.room_id).update(is_active=state)

    # Events

    async def user_joined(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_joined',
            'username': event['username'],
            'users': event['users'],
        }))

    async def user_left(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'username': event['username'],
            'users': event['users'],
        }))

    async def kicked_handler(self, event):
        if self.user.id == event['user_id']:
            await self.close(code=4003)

    async def kick(self, user_id):
        if self.user.id != self.room.host_id:
            return await self.close(code=4003)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'kicked_handler',
                'user_id': user_id,
            }
        )


class VideoCalls(RoomConsumer):
    async def receive(self , text_data):
        data = json.loads(text_data)
        action = data.get('type')

        if action == 'kick':
            await self.kick(data.get('user_id'))
        elif action == 'offer':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type':'webrtc_offer',
                    'offer':data['offer'],
                    'sender':self.username,
                    'target':data.get('target'),
                }
            )
        elif action == 'answer':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type':'webrtc_answer',
                    'offer':data['offer'],
                    'sender':self.username,
                    'target':data.get('target'),
                }
            )
        elif action == 'ice_candidate':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type':'webrtc_ice',
                    'offer':data['offer'],
                    'sender':self.username,
                    'target':data.get('target'),
                }
            )
    
    async def webrtc_offer(self, event):
        # Only send to the intended target
        if event.get('target') == self.username:
            await self.send(text_data=json.dumps({
                'type': 'offer',
                'offer': event['offer'],
                'sender': event['sender'],
            }))
    
    async def webrtc_answer(self, event):
        if event.get('target') == self.username:
            await self.send(text_data=json.dumps({
                'type': 'answer',
                'answer': event['answer'],
                'sender': event['sender'],
            }))

    async def webrtc_ice(self, event):
        if event.get('target') == self.username:
            await self.send(text_data=json.dumps({
                'type': 'ice_candidate',
                'candidate': event['candidate'],
                'sender': event['sender'],
            }))


class Messaging(RoomConsumer):
    pass
