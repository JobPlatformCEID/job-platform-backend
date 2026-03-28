from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase, TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from channels.routing import URLRouter

from calls.models import Room
from calls.routing import websocket_urlpatterns
from core.asgi import application
from users.models import User, EmployerProfile, CandidateProfile

test_app = URLRouter(websocket_urlpatterns)


class RoomWebSocketTests(TransactionTestCase):

    def setUp(self):
        self.employer = User.objects.create_user(
            username='employer1', password='password', role=User.Role.EMPLOYER
        )
        EmployerProfile.objects.create(user=self.employer, company_name='Test Co')

        self.candidate = User.objects.create_user(
            username='candidate1', password='password', role=User.Role.CANDIDATE
        )
        CandidateProfile.objects.create(user=self.candidate)

        self.room = Room.objects.create(
            room_name='Test Room',
            host=self.employer,
            meeting_date=timezone.now() - timedelta(minutes=5),
            is_active=False
        )

    def tearDown(self):
        # Clears the in-memory store after every WebSocket test
        from calls.consumers import InMemoryUserStore
        InMemoryUserStore.clear()
        super().tearDown()

    async def test_anonymous_cannot_connect(self):
        communicator = WebsocketCommunicator(application, f'/ws/calls/{self.room.id}/')
        connected, _ = await communicator.connect()
        response = await communicator.receive_output()
        self.assertEqual(response['type'], 'websocket.close')
        self.assertEqual(response['code'], 4001)
        await communicator.disconnect()

    async def test_host_can_connect(self):
        communicator = WebsocketCommunicator(test_app, f'/ws/calls/{self.room.id}/')
        communicator.scope['user'] = self.employer
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.receive_json_from()
        await communicator.disconnect()

    async def test_candidate_blocked_before_host(self):
        communicator = WebsocketCommunicator(test_app, f'/ws/calls/{self.room.id}/')
        communicator.scope['user'] = self.candidate
        await communicator.connect()
        response = await communicator.receive_output()
        self.assertEqual(response['type'], 'websocket.close')
        self.assertEqual(response['code'], 4004)
        await communicator.disconnect()

    async def test_too_early_to_join(self):
        future_room = await Room.objects.acreate(
            room_name='Future',
            host=self.employer,
            meeting_date=timezone.now() + timedelta(hours=2),
            is_active=False
        )
        communicator = WebsocketCommunicator(test_app, f'/ws/calls/{future_room.id}/')
        communicator.scope['user'] = self.employer
        await communicator.connect()
        response = await communicator.receive_output()
        self.assertEqual(response['type'], 'websocket.close')
        self.assertEqual(response['code'], 4003)
        await communicator.disconnect()

    async def test_candidate_can_join_after_host(self):
        comm1 = WebsocketCommunicator(test_app, f'/ws/calls/{self.room.id}/')
        comm1.scope['user'] = self.employer
        await comm1.connect()
        await comm1.receive_json_from()

        comm2 = WebsocketCommunicator(test_app, f'/ws/calls/{self.room.id}/')
        comm2.scope['user'] = self.candidate
        connected, _ = await comm2.connect()
        self.assertTrue(connected)

        await comm1.disconnect()
        await comm2.disconnect()

    async def test_user_joined_broadcast(self):
        communicator = WebsocketCommunicator(test_app, f'/ws/calls/{self.room.id}/')
        communicator.scope['user'] = self.employer
        await communicator.connect()
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'user_joined')
        self.assertEqual(response['username'], self.employer.username)
        await communicator.disconnect()

    async def test_multiple_users_join(self):
        comm1 = WebsocketCommunicator(test_app, f'/ws/calls/{self.room.id}/')
        comm1.scope['user'] = self.employer
        await comm1.connect()
        await comm1.receive_json_from()

        comm2 = WebsocketCommunicator(test_app, f'/ws/calls/{self.room.id}/')
        comm2.scope['user'] = self.candidate
        await comm2.connect()

        response = await comm1.receive_json_from()
        self.assertEqual(response['type'], 'user_joined')
        self.assertEqual(len(response['users']), 2)

        await comm1.disconnect()
        await comm2.disconnect()

    async def test_host_leaving_deactivates_room(self):
        comm = WebsocketCommunicator(test_app, f'/ws/calls/{self.room.id}/')
        comm.scope['user'] = self.employer
        await comm.connect()
        await comm.receive_json_from()
        await comm.disconnect()

        await self.room.arefresh_from_db()
        self.assertFalse(self.room.is_active)


class RoomAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.employer1 = User.objects.create_user(
            username='employer1', password='password', role=User.Role.EMPLOYER
        )
        EmployerProfile.objects.create(user=self.employer1, company_name='Company One')
        self.employer1_token = Token.objects.create(user=self.employer1)

        self.employer2 = User.objects.create_user(
            username='employer2', password='password', role=User.Role.EMPLOYER
        )
        EmployerProfile.objects.create(user=self.employer2, company_name='Company Two')
        self.employer2_token = Token.objects.create(user=self.employer2)

        self.candidate = User.objects.create_user(
            username='candidate1', password='password', role=User.Role.CANDIDATE
        )
        CandidateProfile.objects.create(user=self.candidate)
        self.candidate_token = Token.objects.create(user=self.candidate)

        self.room = Room.objects.create(
            room_name='Test Room',
            host=self.employer1,
            meeting_date=timezone.now() + timedelta(hours=1),
            description='Test interview',
        )

    def tearDown(self):
        # Also clearing here in case API calls triggered consumer side-effects
        from calls.consumers import InMemoryUserStore
        InMemoryUserStore.clear()
        super().tearDown()

    def test_create_room_invalid_data(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.post('/api/calls/', {'room_name': ''})
        self.assertEqual(response.status_code, 400)

    def test_employer_can_create_room(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.post('/api/calls/', {
            'room_name': 'New Interview',
            'meeting_date': (timezone.now() + timedelta(hours=2)).isoformat(),
            'description': 'Technical round'
        })
        self.assertEqual(response.status_code, 201)

    def test_candidate_cannot_create_room(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.post('/api/calls/', {
            'room_name': 'New Interview',
            'meeting_date': (timezone.now() + timedelta(hours=2)).isoformat(),
            'description': 'Technical round'
        })
        self.assertEqual(response.status_code, 403)

    def test_candidate_cannot_delete_room(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.delete(f'/api/calls/{self.room.id}/')
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_cannot_create_room(self):
        response = self.client.post('/api/calls/', {
            'room_name': 'New Interview',
            'meeting_date': (timezone.now() + timedelta(hours=2)).isoformat(),
            'description': 'Technical round'
        })
        self.assertEqual(response.status_code, 401)

    def test_anyone_can_list_rooms(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.get('/api/calls/')
        self.assertEqual(response.status_code, 200)

    def test_anyone_can_get_room(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.get(f'/api/calls/{self.room.id}/')
        self.assertEqual(response.status_code, 200)

    def test_host_can_update_room(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.patch(f'/api/calls/{self.room.id}/', {'room_name': 'Updated Room'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['room_name'], 'Updated Room')

    def test_other_employer_cannot_update_room(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer2_token.key)
        response = self.client.patch(f'/api/calls/{self.room.id}/', {'room_name': 'Hacked'})
        self.assertEqual(response.status_code, 403)

    def test_host_can_delete_room(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.delete(f'/api/calls/{self.room.id}/')
        self.assertEqual(response.status_code, 204)

    def test_other_employer_cannot_delete_room(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer2_token.key)
        response = self.client.delete(f'/api/calls/{self.room.id}/')
        self.assertEqual(response.status_code, 403)

    def test_nonexistent_room_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.get('/api/calls/99999/')
        self.assertEqual(response.status_code, 404)

    def test_room_host_is_set_automatically(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.post('/api/calls/', {
            'room_name': 'Auto Host Room',
            'meeting_date': (timezone.now() + timedelta(hours=2)).isoformat(),
            'description': 'Test'
        })
        self.assertEqual(response.status_code, 201)
        room = Room.objects.get(id=response.data['id'])
        self.assertEqual(room.host, self.employer1)

    def test_cannot_create_past_meeting(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.post('/api/calls/', {
            'room_name': 'Bad Room',
            'meeting_date': (timezone.now() - timedelta(hours=1)).isoformat(),
            'description': 'Invalid'
        })
        self.assertEqual(response.status_code, 400)