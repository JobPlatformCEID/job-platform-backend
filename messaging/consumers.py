import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Conversation, Message, ConversationReadStatus
from users.models import User

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        if not await self.is_participant():
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # Update all read statuses on connect
        last_read_id = await self.update_read_status()
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'messages_read',
                'reader_id': self.user.id,
                'reader_username': self.user.username,
                'last_read_message_id': last_read_id,
            }
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        content = data.get('content', '').strip()
        msg_type = data.get('type')

        # Check if it's a read acknowledgment from the client
        if msg_type == 'read':
            message_id = data.get('message_id')
            if message_id:
                # Client sent a read receipt: Update last read id in the server
                last_read_id = await self.update_read_status_for_message(message_id)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'messages_read',
                        'reader_id': self.user.id,
                        'reader_username': self.user.username,
                        'last_read_message_id': last_read_id,
                    }
                )
            return

        if not content:
            return
        message = await self.save_message(content)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message_id': message.id,
                'content': message.content,
                'sender_id': self.user.id,
                'sender_username': self.user.username,
                'created_at': str(message.created_at),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message_id': event['message_id'],
            'content': event['content'],
            'sender_id': event['sender_id'],
            'sender_username': event['sender_username'],
            'created_at': event['created_at'],
        }))

    async def messages_read(self, event):
        if event['reader_id'] == self.user.id:
            return
        await self.send(text_data=json.dumps({
            'type': 'read',
            'reader_id': event['reader_id'],
            'reader_username': event['reader_username'],
            'last_read_message_id': event.get('last_read_message_id', 0),
        }))

    @database_sync_to_async
    def is_participant(self):
        try:
            conversation = Conversation.objects.get(pk=self.conversation_id)
            return self.user in conversation.participants.all()
        except Conversation.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, content):
        conversation = Conversation.objects.get(pk=self.conversation_id)
        return Message.objects.create(
            conversation=conversation,
            sender=self.user,
            content=content
        )

    @database_sync_to_async
    def update_read_status(self):
        last_message = Message.objects.filter(
            conversation_id=self.conversation_id
        ).exclude(
            sender=self.user
        ).order_by('-id').first()

        last_read_id = last_message.id if last_message else 0

        ConversationReadStatus.objects.update_or_create(
            conversation_id=self.conversation_id,
            user=self.user,
            defaults={'last_read_message_id': last_read_id}
        )
        return last_read_id

    @database_sync_to_async
    def update_read_status_for_message(self, message_id):
        ConversationReadStatus.objects.update_or_create(
            conversation_id=self.conversation_id,
            user=self.user,
            defaults={'last_read_message_id': message_id}
        )
        return message_id
