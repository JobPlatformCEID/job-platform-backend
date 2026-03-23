from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from users.models import User, EmployerProfile
from .models import Conversation, Message
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from core.asgi import application
from django.test import TransactionTestCase

class ConversationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user1 = User.objects.create_user(
            username='user1',
            password='password',
            role=User.Role.CANDIDATE
        )
        self.user1_token = Token.objects.create(user=self.user1)

        self.user2 = User.objects.create_user(
            username='user2',
            password='password',
            role=User.Role.CANDIDATE
        )
        self.user2_token = Token.objects.create(user=self.user2)

        self.user3 = User.objects.create_user(
            username='user3',
            password='password',
            role=User.Role.CANDIDATE
        )
        self.user3_token = Token.objects.create(user=self.user3)

        self.employer1 = User.objects.create_user(
            username='employer1',
            password='password',
            role=User.Role.EMPLOYER
        )
        EmployerProfile.objects.create(user=self.employer1, company_name='Company One')
        self.employer1_token = Token.objects.create(user=self.employer1)

    def test_user_can_create_conversation(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.post('/api/conversations/', {'user_id': self.user2.id})
        self.assertEqual(response.status_code, 201)

    def test_employer_can_create_conversation(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.post('/api/conversations/', {'user_id': self.user1.id})
        self.assertEqual(response.status_code, 201)

    def test_duplicate_conversation_returns_existing(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        self.client.post('/api/conversations/', {'user_id': self.user2.id})
        response = self.client.post('/api/conversations/', {'user_id': self.user2.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Conversation.objects.count(), 1)

    def test_cannot_create_conversation_with_self(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.post('/api/conversations/', {'user_id': self.user1.id})
        self.assertEqual(response.status_code, 400)

    def test_cannot_create_conversation_with_nonexistent_user(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.post('/api/conversations/', {'user_id': 9999})
        self.assertEqual(response.status_code, 404)

    def test_cannot_create_conversation_without_user_id(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.post('/api/conversations/', {})
        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_user_cannot_create_conversation(self):
        self.client.credentials()
        response = self.client.post('/api/conversations/', {'user_id': self.user2.id})
        self.assertEqual(response.status_code, 401)

    def test_user_can_list_own_conversations(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        self.client.post('/api/conversations/', {'user_id': self.user2.id})
        response = self.client.get('/api/conversations/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_user_cannot_see_other_users_conversations(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        self.client.post('/api/conversations/', {'user_id': self.user2.id})
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user3_token.key)
        response = self.client.get('/api/conversations/')
        self.assertEqual(len(response.data), 0)

    def test_participant_can_delete_conversation(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.post('/api/conversations/', {'user_id': self.user2.id})
        conversation_id = response.data['id']
        response = self.client.delete(f'/api/conversations/{conversation_id}/')
        self.assertEqual(response.status_code, 204)

    def test_non_participant_cannot_delete_conversation(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.post('/api/conversations/', {'user_id': self.user2.id})
        conversation_id = response.data['id']
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user3_token.key)
        response = self.client.delete(f'/api/conversations/{conversation_id}/')
        self.assertEqual(response.status_code, 403)

    def test_deleting_conversation_deletes_messages(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.post('/api/conversations/', {'user_id': self.user2.id})
        conversation_id = response.data['id']
        conversation = Conversation.objects.get(pk=conversation_id)
        Message.objects.create(conversation=conversation, sender=self.user1, content='Hello')
        Message.objects.create(conversation=conversation, sender=self.user2, content='Hi')
        self.client.delete(f'/api/conversations/{conversation_id}/')
        self.assertEqual(Message.objects.filter(conversation_id=conversation_id).count(), 0)

    def test_delete_nonexistent_conversation(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.delete('/api/conversations/9999/')
        self.assertEqual(response.status_code, 404)

class MessageTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user1 = User.objects.create_user(
            username='user1',
            password='password',
            role=User.Role.CANDIDATE
        )
        self.user1_token = Token.objects.create(user=self.user1)

        self.user2 = User.objects.create_user(
            username='user2',
            password='password',
            role=User.Role.CANDIDATE
        )
        self.user2_token = Token.objects.create(user=self.user2)

        self.user3 = User.objects.create_user(
            username='user3',
            password='password',
            role=User.Role.CANDIDATE
        )
        self.user3_token = Token.objects.create(user=self.user3)

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.post('/api/conversations/', {'user_id': self.user2.id})
        self.conversation_id = response.data['id']

        conversation = Conversation.objects.get(pk=self.conversation_id)
        Message.objects.create(conversation=conversation, sender=self.user1, content='Hello')
        Message.objects.create(conversation=conversation, sender=self.user2, content='Hi')

    def test_participant_can_list_messages(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.get(f'/api/conversations/{self.conversation_id}/messages/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_other_participant_can_list_messages(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user2_token.key)
        response = self.client.get(f'/api/conversations/{self.conversation_id}/messages/')
        self.assertEqual(response.status_code, 200)

    def test_non_participant_cannot_list_messages(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user3_token.key)
        response = self.client.get(f'/api/conversations/{self.conversation_id}/messages/')
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_user_cannot_list_messages(self):
        self.client.credentials()
        response = self.client.get(f'/api/conversations/{self.conversation_id}/messages/')
        self.assertEqual(response.status_code, 401)

    def test_messages_in_nonexistent_conversation(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.get('/api/conversations/9999/messages/')
        self.assertEqual(response.status_code, 404)

    def test_sender_can_delete_message(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.get(f'/api/conversations/{self.conversation_id}/messages/')
        message_id = response.data[0]['id']
        response = self.client.delete(f'/api/conversations/{self.conversation_id}/messages/{message_id}/')
        self.assertEqual(response.status_code, 204)

    def test_non_sender_cannot_delete_message(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.get(f'/api/conversations/{self.conversation_id}/messages/')
        message_id = response.data[0]['id']
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user2_token.key)
        response = self.client.delete(f'/api/conversations/{self.conversation_id}/messages/{message_id}/')
        self.assertEqual(response.status_code, 403)

    def test_delete_nonexistent_message(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.delete(f'/api/conversations/{self.conversation_id}/messages/9999/')
        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_user_cannot_delete_message(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.get(f'/api/conversations/{self.conversation_id}/messages/')
        message_id = response.data[0]['id']
        self.client.credentials()
        response = self.client.delete(f'/api/conversations/{self.conversation_id}/messages/{message_id}/')
        self.assertEqual(response.status_code, 401)

class WebSocketTests(TransactionTestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='wsuser1',
            password='password',
            role=User.Role.CANDIDATE
        )
        self.user1_token = Token.objects.create(user=self.user1)

        self.user2 = User.objects.create_user(
            username='wsuser2',
            password='password',
            role=User.Role.CANDIDATE
        )
        self.user2_token = Token.objects.create(user=self.user2)

        self.user3 = User.objects.create_user(
            username='wsuser3',
            password='password',
            role=User.Role.CANDIDATE
        )
        self.user3_token = Token.objects.create(user=self.user3)

        conversation = Conversation.objects.create()
        conversation.participants.add(self.user1, self.user2)
        self.conversation_id = conversation.id

    async def receive_of_type(self, communicator, type):
        while True:
            response = await communicator.receive_json_from()
            if response.get('type') == type:
                return response

    async def test_authenticated_participant_can_connect(self):
        communicator = WebsocketCommunicator(
            application,
            f'/ws/conversations/{self.conversation_id}/?token={self.user1_token.key}'
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_unauthenticated_user_cannot_connect(self):
        communicator = WebsocketCommunicator(
            application,
            f'/ws/conversations/{self.conversation_id}/'
        )
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()

    async def test_non_participant_cannot_connect(self):
        communicator = WebsocketCommunicator(
            application,
            f'/ws/conversations/{self.conversation_id}/?token={self.user3_token.key}'
        )
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()

    async def test_user_can_send_message(self):
        communicator = WebsocketCommunicator(
            application,
            f'/ws/conversations/{self.conversation_id}/?token={self.user1_token.key}'
        )
        await communicator.connect()
        await communicator.send_json_to({'content': 'Hello!'})
        response = await self.receive_of_type(communicator, 'message')
        self.assertEqual(response['content'], 'Hello!')
        self.assertEqual(response['sender_id'], self.user1.id)
        self.assertEqual(response['sender_username'], self.user1.username)
        await communicator.disconnect()

    async def test_message_is_broadcast_to_other_participant(self):
        communicator1 = WebsocketCommunicator(
            application,
            f'/ws/conversations/{self.conversation_id}/?token={self.user1_token.key}'
        )
        communicator2 = WebsocketCommunicator(
            application,
            f'/ws/conversations/{self.conversation_id}/?token={self.user2_token.key}'
        )
        await communicator1.connect()
        await communicator2.connect()
        await communicator1.send_json_to({'content': 'Hello!'})
        response = await self.receive_of_type(communicator2, 'message')
        self.assertEqual(response['content'], 'Hello!')
        self.assertEqual(response['sender_username'], self.user1.username)
        await communicator1.disconnect()
        await communicator2.disconnect()

    async def test_message_is_saved_to_database(self):
        communicator = WebsocketCommunicator(
            application,
            f'/ws/conversations/{self.conversation_id}/?token={self.user1_token.key}'
        )
        await communicator.connect()
        await communicator.send_json_to({'content': 'Hello!'})
        await self.receive_of_type(communicator, 'message')
        count = await database_sync_to_async(Message.objects.filter(
            conversation_id=self.conversation_id
        ).count)()
        self.assertEqual(count, 1)
        await communicator.disconnect()

    async def test_empty_message_is_not_sent(self):
        communicator = WebsocketCommunicator(
            application,
            f'/ws/conversations/{self.conversation_id}/?token={self.user1_token.key}'
        )
        await communicator.connect()
        await self.receive_of_type(communicator, 'read')  # consume read receipt
        await communicator.send_json_to({'content': ''})
        self.assertTrue(await communicator.receive_nothing())
        await communicator.disconnect()

    async def test_messages_marked_as_read_on_connect(self):
        conversation = await database_sync_to_async(Conversation.objects.get)(pk=self.conversation_id)
        await database_sync_to_async(Message.objects.create)(
            conversation=conversation,
            sender=self.user1,
            content='Hello'
        )
        communicator = WebsocketCommunicator(
            application,
            f'/ws/conversations/{self.conversation_id}/?token={self.user2_token.key}'
        )
        await communicator.connect()
        is_read = await database_sync_to_async(
            Message.objects.filter(conversation_id=self.conversation_id, is_read=True).exists
        )()
        self.assertTrue(is_read)
        await communicator.disconnect()

    async def test_own_messages_not_marked_as_read_on_connect(self):
        conversation = await database_sync_to_async(Conversation.objects.get)(pk=self.conversation_id)
        await database_sync_to_async(Message.objects.create)(
            conversation=conversation,
            sender=self.user1,
            content='Hello'
        )
        communicator = WebsocketCommunicator(
            application,
            f'/ws/conversations/{self.conversation_id}/?token={self.user1_token.key}'
        )
        await communicator.connect()
        is_read = await database_sync_to_async(
            Message.objects.filter(conversation_id=self.conversation_id, is_read=True).exists
        )()
        self.assertFalse(is_read)
        await communicator.disconnect()

    async def test_read_receipt_broadcast_on_connect(self):
        communicator1 = WebsocketCommunicator(
            application,
            f'/ws/conversations/{self.conversation_id}/?token={self.user1_token.key}'
        )
        communicator2 = WebsocketCommunicator(
            application,
            f'/ws/conversations/{self.conversation_id}/?token={self.user2_token.key}'
        )
        await communicator1.connect()
        await self.receive_of_type(communicator1, 'read')  # consume user1's own read receipt
        await communicator2.connect()
        response = await self.receive_of_type(communicator1, 'read')  # this should be user2's
        self.assertEqual(response['type'], 'read')
        self.assertEqual(response['reader_id'], self.user2.id)
        await communicator1.disconnect()
        await communicator2.disconnect()
