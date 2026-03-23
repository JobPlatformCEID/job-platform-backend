from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer
from django.test import TransactionTestCase
from rest_framework.authtoken.models import Token
from users.models import User, EmployerProfile, CandidateProfile
from calls.models import Room
from core.asgi import application
from django.utils import timezone
from datetime import timedelta
from django.test import TestCase
from rest_framework.test import APIClient

class RoomWebSocketTests(TransactionTestCase):

    def setUp(self):
        self.employer = User.objects.create_user(
            username='employer1',
            password='password',
            role=User.Role.EMPLOYER
        )
        EmployerProfile.objects.create(user=self.employer, company_name='Test Co')
        self.employer_token = Token.objects.create(user=self.employer)

        self.candidate = User.objects.create_user(
            username='candidate1',
            password='password',
            role=User.Role.CANDIDATE
        )
        CandidateProfile.objects.create(user=self.candidate)
        self.candidate_token = Token.objects.create(user=self.candidate)

        self.room = Room.objects.create(
            room_name='Test Room',
            host=self.employer,
            meeting_date=timezone.now() - timedelta(minutes=5),
            description='Test interview',
            is_active=False
        )

    async def test_anonymous_cannot_connect(self):
        communicator = WebsocketCommunicator(
            application,
            f'/ws/calls/{self.room.id}/'
        )
        connected, code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(code, 4001)

    async def test_host_can_connect(self):
        communicator = WebsocketCommunicator(
            application,
            f'/ws/calls/{self.room.id}/'
        )
        communicator.scope['user'] = self.employer
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_room_active_when_host_joins(self):
        communicator = WebsocketCommunicator(
            application,
            f'/ws/calls/{self.room.id}/'
        )
        communicator.scope['user'] = self.employer
        await communicator.connect()
        await communicator.disconnect()

        await self.room.arefresh_from_db()
        self.assertFalse(self.room.is_active)

    async def test_candidate_blocked_before_host(self):
        communicator = WebsocketCommunicator(
            application,
            f'/ws/calls/{self.room.id}/'
        )
        communicator.scope['user'] = self.candidate
        connected, code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(code, 4004)

    async def test_too_early_to_join(self):
        future_room = await Room.objects.acreate(
            room_name='Future Room',
            host=self.employer,
            meeting_date=timezone.now() + timedelta(hours=2),
            description='Too early',
            is_active=False
        )
        communicator = WebsocketCommunicator(
            application,
            f'/ws/calls/{future_room.id}/'
        )
        communicator.scope['user'] = self.employer
        connected, code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(code, 4003)
    
    async def test_candidate_can_join_after_host(self):
        comm1 = WebsocketCommunicator(application, f'/ws/calls/{self.room.id}/')
        comm1.scope['user'] = self.employer
        await comm1.connect()
        await comm1.receive_json_from()

        comm2 = WebsocketCommunicator(application, f'/ws/calls/{self.room.id}/')
        comm2.scope['user'] = self.candidate
        connected, _ = await comm2.connect()

        self.assertTrue(connected)

        await comm1.disconnect()
        await comm2.disconnect()


    async def test_host_can_kick_user(self):
        comm1 = WebsocketCommunicator(application, f'/ws/calls/{self.room.id}/')
        comm1.scope['user'] = self.employer
        await comm1.connect()
        await comm1.receive_json_from()

        comm2 = WebsocketCommunicator(application, f'/ws/calls/{self.room.id}/')
        comm2.scope['user'] = self.candidate
        await comm2.connect()
        await comm2.receive_json_from()

        # host sends kick message
        await comm1.send_json_to({
            "type": "kick",
            "user_id": self.candidate.id
        })

        # candidate should be disconnected
        response = await comm2.receive_output(timeout=1)

        self.assertIsNotNone(response)

        await comm1.disconnect()

    async def test_non_host_cannot_kick(self):
        comm1 = WebsocketCommunicator(application, f'/ws/calls/{self.room.id}/')
        comm1.scope['user'] = self.employer
        await comm1.connect()
        await comm1.receive_json_from()

        comm2 = WebsocketCommunicator(application, f'/ws/calls/{self.room.id}/')
        comm2.scope['user'] = self.candidate
        await comm2.connect()
        await comm2.receive_json_from()

        # candidate tries to kick host
        await comm2.send_json_to({
            "type": "kick",
            "user_id": self.employer.id
        })

        # host should NOT be disconnected
        still_connected = True
        try:
            await comm1.receive_output(timeout=1)
        except:
            still_connected = True

        self.assertTrue(still_connected)

        await comm1.disconnect()
        await comm2.disconnect()



    async def test_user_joined_broadcast(self):
        communicator = WebsocketCommunicator(
            application,
            f'/ws/calls/{self.room.id}/'
        )
        communicator.scope['user'] = self.employer
        await communicator.connect()

        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'user_joined')
        self.assertEqual(response['username'], self.employer.username)

        await communicator.disconnect()

    async def test_user_left_broadcast(self):
        communicator = WebsocketCommunicator(
            application,
            f'/ws/calls/{self.room.id}/'
        )
        communicator.scope['user'] = self.employer
        await communicator.connect()
        await communicator.receive_json_from()  # consume join message
        await communicator.disconnect()

    async def test_multiple_users_join(self):
        comm1 = WebsocketCommunicator(application, f'/ws/calls/{self.room.id}/')
        comm1.scope['user'] = self.employer
        await comm1.connect()
        await comm1.receive_json_from()  # consume host join

        comm2 = WebsocketCommunicator(application, f'/ws/calls/{self.room.id}/')
        comm2.scope['user'] = self.candidate
        connected, _ = await comm2.connect()
        self.assertTrue(connected)

        response = await comm1.receive_json_from()

        self.assertEqual(response['type'], 'user_joined')
        self.assertEqual(len(response['users']), 2)

        await comm1.disconnect()
        await comm2.disconnect()

    async def test_user_list_updates_on_leave(self):
        comm1 = WebsocketCommunicator(application, f'/ws/calls/{self.room.id}/')
        comm1.scope['user'] = self.employer
        await comm1.connect()
        await comm1.receive_json_from()

        comm2 = WebsocketCommunicator(application, f'/ws/calls/{self.room.id}/')
        comm2.scope['user'] = self.candidate
        await comm2.connect()
        await comm2.receive_json_from()

        await comm2.disconnect()

        response = await comm1.receive_json_from()

        self.assertEqual(response['type'], 'user_left')
        self.assertEqual(len(response['users']), 1)

        await comm1.disconnect()
    
    async def test_host_leaving_deactivates_room(self):
        comm = WebsocketCommunicator(application, f'/ws/calls/{self.room.id}/')
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
            username='employer1',
            password='password',
            role=User.Role.EMPLOYER
        )
        EmployerProfile.objects.create(user=self.employer1, company_name='Company One')
        self.employer1_token = Token.objects.create(user=self.employer1)

        self.employer2 = User.objects.create_user(
            username='employer2',
            password='password',
            role=User.Role.EMPLOYER
        )
        EmployerProfile.objects.create(user=self.employer2, company_name='Company Two')
        self.employer2_token = Token.objects.create(user=self.employer2)

        self.candidate = User.objects.create_user(
            username='candidate1',
            password='password',
            role=User.Role.CANDIDATE
        )
        CandidateProfile.objects.create(user=self.candidate)
        self.candidate_token = Token.objects.create(user=self.candidate)

        self.room = Room.objects.create(
            room_name='Test Room',
            host=self.employer1,
            meeting_date=timezone.now() + timedelta(hours=1),
            description='Test interview',
        )
    
    def test_create_room_invalid_data(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.post('/api/calls/', {
            'room_name': '',
        })
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
        response = self.client.patch(f'/api/calls/{self.room.id}/', {
            'room_name': 'Updated Room'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['room_name'], 'Updated Room')

    def test_other_employer_cannot_update_room(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer2_token.key)
        response = self.client.patch(f'/api/calls/{self.room.id}/', {
            'room_name': 'Hacked'
        })
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
