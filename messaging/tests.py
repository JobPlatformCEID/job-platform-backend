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
        await communicator.send_json_to({'content': ''})
        self.assertTrue(await communicator.receive_nothing())
        await communicator.disconnect()

    async def test_read_status_updated_on_connect(self):
        from messaging.models import ConversationReadStatus
        conversation = await database_sync_to_async(Conversation.objects.get)(pk=self.conversation_id)
        message = await database_sync_to_async(Message.objects.create)(
            conversation=conversation,
            sender=self.user1,
            content='Hello'
        )
        communicator = WebsocketCommunicator(
            application,
            f'/ws/conversations/{self.conversation_id}/?token={self.user2_token.key}'
        )
        await communicator.connect()
        status = await database_sync_to_async(ConversationReadStatus.objects.get)(
            conversation_id=self.conversation_id,
            user=self.user2
        )
        self.assertEqual(status.last_read_message_id, message.id)
        await communicator.disconnect()

    async def test_own_messages_not_counted_in_read_status(self):
        from messaging.models import ConversationReadStatus
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
        status = await database_sync_to_async(ConversationReadStatus.objects.filter(
            conversation_id=self.conversation_id,
            user=self.user1
        ).first)()
        # user1 sent the message so last_read_message_id should be 0
        self.assertEqual(status.last_read_message_id if status else 0, 0)
        await communicator.disconnect()

    async def test_read_receipt_includes_last_read_message_id(self):
        from messaging.models import ConversationReadStatus
        conversation = await database_sync_to_async(Conversation.objects.get)(pk=self.conversation_id)
        message = await database_sync_to_async(Message.objects.create)(
            conversation=conversation,
            sender=self.user1,
            content='Hello'
        )
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
        response = await self.receive_of_type(communicator1, 'read')
        self.assertEqual(response['last_read_message_id'], message.id)
        await communicator1.disconnect()
        await communicator2.disconnect()

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
        await communicator2.connect()
        response = await self.receive_of_type(communicator1, 'read')  # this should be user2's receipt
        self.assertEqual(response['type'], 'read')
        self.assertEqual(response['reader_id'], self.user2.id)
        await communicator1.disconnect()
        await communicator2.disconnect()


class ConversationFieldTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user1 = User.objects.create_user(username='u1', password='password', role=User.Role.CANDIDATE)
        self.user1_token = Token.objects.create(user=self.user1)

        self.user2 = User.objects.create_user(username='u2', password='password', role=User.Role.CANDIDATE)
        self.user2_token = Token.objects.create(user=self.user2)

        self.user3 = User.objects.create_user(username='u3', password='password', role=User.Role.CANDIDATE)
        self.user3_token = Token.objects.create(user=self.user3)

    def test_create_conversation_response_contains_expected_fields(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.post('/api/conversations/', {'user_id': self.user2.id})
        self.assertEqual(response.status_code, 201)
        for field in ('id', 'participants', 'created_at', 'last_message', 'other_user', 'read_statuses'):
            self.assertIn(field, response.data)

    def test_other_user_field_contains_correct_user(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.post('/api/conversations/', {'user_id': self.user2.id})
        self.assertEqual(response.data['other_user']['id'], self.user2.id)
        self.assertEqual(response.data['other_user']['username'], self.user2.username)

    def test_other_user_is_relative_to_requester(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        r = self.client.post('/api/conversations/', {'user_id': self.user2.id})
        conversation_id = r.data['id']

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user2_token.key)
        response = self.client.get('/api/conversations/')
        conv = next(c for c in response.data if c['id'] == conversation_id)
        self.assertEqual(conv['other_user']['id'], self.user1.id)

    def test_last_message_is_none_on_new_conversation(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.post('/api/conversations/', {'user_id': self.user2.id})
        self.assertIsNone(response.data['last_message'])

    def test_last_message_reflects_most_recent_message(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        r = self.client.post('/api/conversations/', {'user_id': self.user2.id})
        conversation_id = r.data['id']
        conversation = Conversation.objects.get(pk=conversation_id)
        Message.objects.create(conversation=conversation, sender=self.user1, content='First')
        last = Message.objects.create(conversation=conversation, sender=self.user2, content='Last')

        response = self.client.get('/api/conversations/')
        conv = next(c for c in response.data if c['id'] == conversation_id)
        self.assertEqual(conv['last_message']['id'], last.id)
        self.assertEqual(conv['last_message']['content'], 'Last')

    def test_read_statuses_empty_on_new_conversation(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.post('/api/conversations/', {'user_id': self.user2.id})
        self.assertEqual(response.data['read_statuses'], {})

    def test_both_participants_appear_in_participants_list(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.post('/api/conversations/', {'user_id': self.user2.id})
        ids = response.data['participants']
        self.assertIn(self.user1.id, ids)
        self.assertIn(self.user2.id, ids)

    def test_conversation_appears_in_both_participants_lists(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        r = self.client.post('/api/conversations/', {'user_id': self.user2.id})
        conversation_id = r.data['id']

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user2_token.key)
        response = self.client.get('/api/conversations/')
        ids = [c['id'] for c in response.data]
        self.assertIn(conversation_id, ids)

    def test_unauthenticated_cannot_list_conversations(self):
        self.client.credentials()
        response = self.client.get('/api/conversations/')
        self.assertEqual(response.status_code, 401)

    def test_multiple_conversations_listed(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        self.client.post('/api/conversations/', {'user_id': self.user2.id})
        self.client.post('/api/conversations/', {'user_id': self.user3.id})
        response = self.client.get('/api/conversations/')
        self.assertEqual(len(response.data), 2)

    def test_unauthenticated_cannot_delete_conversation(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        r = self.client.post('/api/conversations/', {'user_id': self.user2.id})
        conversation_id = r.data['id']
        self.client.credentials()
        response = self.client.delete(f'/api/conversations/{conversation_id}/')
        self.assertEqual(response.status_code, 401)

    def test_delete_removes_conversation_from_db(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        r = self.client.post('/api/conversations/', {'user_id': self.user2.id})
        conversation_id = r.data['id']
        self.client.delete(f'/api/conversations/{conversation_id}/')
        self.assertFalse(Conversation.objects.filter(pk=conversation_id).exists())

    def test_other_participant_can_also_delete_conversation(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        r = self.client.post('/api/conversations/', {'user_id': self.user2.id})
        conversation_id = r.data['id']
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user2_token.key)
        response = self.client.delete(f'/api/conversations/{conversation_id}/')
        self.assertEqual(response.status_code, 204)

    def test_full_name_in_other_user_with_names_set(self):
        self.user2.first_name = 'Jane'
        self.user2.last_name = 'Doe'
        self.user2.save()
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.post('/api/conversations/', {'user_id': self.user2.id})
        self.assertEqual(response.data['other_user']['full_name'], 'Jane Doe')

    def test_full_name_falls_back_to_username_in_other_user(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.post('/api/conversations/', {'user_id': self.user2.id})
        self.assertEqual(response.data['other_user']['full_name'], self.user2.username)


class MessageFieldTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user1 = User.objects.create_user(username='u1', password='password', role=User.Role.CANDIDATE)
        self.user1_token = Token.objects.create(user=self.user1)

        self.user2 = User.objects.create_user(username='u2', password='password', role=User.Role.CANDIDATE)
        self.user2_token = Token.objects.create(user=self.user2)

        self.user3 = User.objects.create_user(username='u3', password='password', role=User.Role.CANDIDATE)
        self.user3_token = Token.objects.create(user=self.user3)

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        r = self.client.post('/api/conversations/', {'user_id': self.user2.id})
        self.conversation_id = r.data['id']
        self.conversation = Conversation.objects.get(pk=self.conversation_id)

        self.msg1 = Message.objects.create(conversation=self.conversation, sender=self.user1, content='Hello')
        self.msg2 = Message.objects.create(conversation=self.conversation, sender=self.user2, content='Hi')

    def test_messages_contain_expected_fields(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.get(f'/api/conversations/{self.conversation_id}/messages/')
        msg = response.data[0]
        for field in ('id', 'content', 'sender', 'conversation', 'created_at'):
            self.assertIn(field, msg)

    def test_messages_ordered_oldest_first(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.get(f'/api/conversations/{self.conversation_id}/messages/')
        self.assertEqual(response.data[0]['content'], 'Hello')
        self.assertEqual(response.data[1]['content'], 'Hi')

    def test_message_sender_matches_creator(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.get(f'/api/conversations/{self.conversation_id}/messages/')
        self.assertEqual(response.data[0]['sender'], self.user1.id)

    def test_delete_removes_message_from_db(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.delete(
            f'/api/conversations/{self.conversation_id}/messages/{self.msg1.id}/'
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Message.objects.filter(pk=self.msg1.id).exists())

    def test_message_count_decreases_after_delete(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        self.client.delete(f'/api/conversations/{self.conversation_id}/messages/{self.msg1.id}/')
        response = self.client.get(f'/api/conversations/{self.conversation_id}/messages/')
        self.assertEqual(len(response.data), 1)

    def test_delete_message_from_wrong_conversation_returns_404(self):
        other_conv = Conversation.objects.create()
        other_conv.participants.add(self.user1, self.user3)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.delete(
            f'/api/conversations/{other_conv.id}/messages/{self.msg1.id}/'
        )
        self.assertEqual(response.status_code, 404)

    def test_non_participant_cannot_delete_message(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user3_token.key)
        response = self.client.delete(
            f'/api/conversations/{self.conversation_id}/messages/{self.msg1.id}/'
        )
        self.assertEqual(response.status_code, 404)


class ConversationModelTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='u1', password='password', role=User.Role.CANDIDATE)
        self.user2 = User.objects.create_user(username='u2', password='password', role=User.Role.CANDIDATE)

    def test_conversation_created_at_set_automatically(self):
        conv = Conversation.objects.create()
        self.assertIsNotNone(conv.created_at)

    def test_participants_can_be_added(self):
        conv = Conversation.objects.create()
        conv.participants.add(self.user1, self.user2)
        self.assertEqual(conv.participants.count(), 2)

    def test_messages_cascade_deleted_with_conversation(self):
        conv = Conversation.objects.create()
        conv.participants.add(self.user1, self.user2)
        msg = Message.objects.create(conversation=conv, sender=self.user1, content='Hi')
        msg_id = msg.pk
        conv.delete()
        self.assertFalse(Message.objects.filter(pk=msg_id).exists())

    def test_conversation_ordering_newest_first(self):
        conv1 = Conversation.objects.create()
        conv2 = Conversation.objects.create()
        convs = list(Conversation.objects.all())
        self.assertEqual(convs[0].pk, conv2.pk)

    def test_read_status_unique_together(self):
        from django.db import IntegrityError
        from messaging.models import ConversationReadStatus
        conv = Conversation.objects.create()
        conv.participants.add(self.user1, self.user2)
        ConversationReadStatus.objects.create(conversation=conv, user=self.user1, last_read_message_id=0)
        with self.assertRaises(IntegrityError):
            ConversationReadStatus.objects.create(conversation=conv, user=self.user1, last_read_message_id=1)

    def test_message_ordering_oldest_first(self):
        conv = Conversation.objects.create()
        conv.participants.add(self.user1, self.user2)
        m1 = Message.objects.create(conversation=conv, sender=self.user1, content='First')
        m2 = Message.objects.create(conversation=conv, sender=self.user2, content='Second')
        messages = list(Message.objects.filter(conversation=conv))
        self.assertEqual(messages[0].pk, m1.pk)
        self.assertEqual(messages[1].pk, m2.pk)


class WebSocketExtendedTests(TransactionTestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='wsext1', password='password', role=User.Role.CANDIDATE)
        self.user1_token = Token.objects.create(user=self.user1)

        self.user2 = User.objects.create_user(username='wsext2', password='password', role=User.Role.CANDIDATE)
        self.user2_token = Token.objects.create(user=self.user2)

        conversation = Conversation.objects.create()
        conversation.participants.add(self.user1, self.user2)
        self.conversation_id = conversation.id

    async def receive_of_type(self, communicator, type, timeout=3):
        while True:
            response = await communicator.receive_json_from(timeout=timeout)
            if response.get('type') == type:
                return response

    async def test_sent_message_contains_expected_fields(self):
        communicator = WebsocketCommunicator(
            application,
            f'/ws/conversations/{self.conversation_id}/?token={self.user1_token.key}'
        )
        await communicator.connect()
        await communicator.send_json_to({'content': 'Check fields'})
        response = await self.receive_of_type(communicator, 'message')
        for field in ('type', 'message_id', 'content', 'sender_id', 'sender_username', 'created_at'):
            self.assertIn(field, response)
        await communicator.disconnect()

    async def test_whitespace_only_message_is_not_sent(self):
        communicator = WebsocketCommunicator(
            application,
            f'/ws/conversations/{self.conversation_id}/?token={self.user1_token.key}'
        )
        await communicator.connect()
        await communicator.send_json_to({'content': '   '})
        self.assertTrue(await communicator.receive_nothing())
        await communicator.disconnect()

    async def test_message_saved_with_correct_sender(self):
        communicator = WebsocketCommunicator(
            application,
            f'/ws/conversations/{self.conversation_id}/?token={self.user1_token.key}'
        )
        await communicator.connect()
        await communicator.send_json_to({'content': 'From user1'})
        await self.receive_of_type(communicator, 'message')
        msg = await database_sync_to_async(
            Message.objects.filter(conversation_id=self.conversation_id).first
        )()
        self.assertEqual(msg.sender_id, self.user1.id)
        await communicator.disconnect()

    async def test_message_saved_with_correct_content(self):
        communicator = WebsocketCommunicator(
            application,
            f'/ws/conversations/{self.conversation_id}/?token={self.user1_token.key}'
        )
        await communicator.connect()
        await communicator.send_json_to({'content': 'Specific content'})
        await self.receive_of_type(communicator, 'message')
        msg = await database_sync_to_async(
            Message.objects.filter(conversation_id=self.conversation_id).first
        )()
        self.assertEqual(msg.content, 'Specific content')
        await communicator.disconnect()

    async def test_sender_also_receives_own_message(self):
        communicator = WebsocketCommunicator(
            application,
            f'/ws/conversations/{self.conversation_id}/?token={self.user1_token.key}'
        )
        await communicator.connect()
        await communicator.send_json_to({'content': 'Echo test'})
        response = await self.receive_of_type(communicator, 'message')
        self.assertEqual(response['content'], 'Echo test')
        await communicator.disconnect()

    async def test_read_event_not_sent_to_own_reader(self):
        communicator = WebsocketCommunicator(
            application,
            f'/ws/conversations/{self.conversation_id}/?token={self.user1_token.key}'
        )
        await communicator.connect()
        self.assertTrue(await communicator.receive_nothing())
        await communicator.disconnect()

    async def test_manual_read_receipt_updates_db(self):
        from messaging.models import ConversationReadStatus
        conversation = await database_sync_to_async(Conversation.objects.get)(pk=self.conversation_id)
        message = await database_sync_to_async(Message.objects.create)(
            conversation=conversation,
            sender=self.user1,
            content='Read me'
        )
        communicator = WebsocketCommunicator(
            application,
            f'/ws/conversations/{self.conversation_id}/?token={self.user2_token.key}'
        )
        await communicator.connect()
        await communicator.send_json_to({'type': 'read', 'message_id': message.id})
        await communicator.receive_nothing()
        status = await database_sync_to_async(ConversationReadStatus.objects.get)(
            conversation_id=self.conversation_id,
            user=self.user2
        )
        self.assertEqual(status.last_read_message_id, message.id)
        await communicator.disconnect()

    async def test_manual_read_receipt_broadcast_to_other_participant(self):
        from messaging.models import ConversationReadStatus
        conversation = await database_sync_to_async(Conversation.objects.get)(pk=self.conversation_id)
        message = await database_sync_to_async(Message.objects.create)(
            conversation=conversation,
            sender=self.user1,
            content='Read me'
        )
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
        await communicator2.send_json_to({'type': 'read', 'message_id': message.id})
        response = await self.receive_of_type(communicator1, 'read')
        self.assertEqual(response['reader_id'], self.user2.id)
        self.assertEqual(response['last_read_message_id'], message.id)
        await communicator1.disconnect()
        await communicator2.disconnect()

    async def test_read_receipt_not_echoed_back_to_sender_of_receipt(self):
        communicator = WebsocketCommunicator(
            application,
            f'/ws/conversations/{self.conversation_id}/?token={self.user1_token.key}'
        )
        await communicator.connect()
        await communicator.send_json_to({'type': 'read', 'message_id': 1})
        self.assertTrue(await communicator.receive_nothing())
        await communicator.disconnect()

    async def test_multiple_messages_all_broadcast(self):
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
        await communicator1.send_json_to({'content': 'One'})
        await communicator1.send_json_to({'content': 'Two'})
        r1 = await self.receive_of_type(communicator2, 'message')
        r2 = await self.receive_of_type(communicator2, 'message')
        contents = {r1['content'], r2['content']}
        self.assertEqual(contents, {'One', 'Two'})
        await communicator1.disconnect()
        await communicator2.disconnect()