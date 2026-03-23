from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Room
import redis.asyncio as redis
import json


class RoomConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        if self.scope['user'].is_anonymous:
            return await self.close(code=4001)

        # Redis connection
        self.redis = redis.Redis(host="redis", port=6379, decode_responses=True)

        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f"calls_{self.room_id}"
        self.redis_key = f"room:{self.room_id}:users"

        self.user = self.scope["user"]
        self.username = self.user.username

        self.room = await self.get_room()

        # too early
        if timezone.now() < self.room.meeting_date:
            return await self.close(code=4003)
        
        #when a host joins the room is active
        if self.user.id == self.room.host.id : 
            await self.set_room_active(True)

        # non-host blocked until host joins
        if not self.room.is_active and self.user.id != self.room.host.id:
            users = await self.get_room_users()
            if not any(u['id'] == self.room.host.id for u in users):
                return await self.close(code=4004)

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        await self.add_user_to_room()

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'username': self.username,
                'users': await self.get_room_users(),
            },
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)

        action = data.get('type')

        if action == 'kick':
            await self.kick(data.get('user_id'))


    async def disconnect(self, code):
        if not hasattr(self, 'room_group_name'):
            return

        await self.remove_user_from_room()

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'username': self.username,
                'users': await self.get_room_users(),
            },
        )

        #for now set it to false until we decide if the call should close when host leaves
        if self.user.id == self.room.host.id:
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
    
    async def kick(self , user_id ):
        if self.user.id != self.room.host.id:
            return await self.close(code=4003)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'kicked_handler',
                'user_id': user_id,
            }
        )


class Messaging(RoomConsumer):
    pass


class VideoCalls(RoomConsumer):
    pass