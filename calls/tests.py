from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from calls.models import Room
from users.models import User, EmployerProfile, CandidateProfile


class RoomListCreateViewTests(TestCase):

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
        self.room.participants.add(self.employer1)

    def test_unauthenticated_cannot_list_rooms(self):
        response = self.client.get('/api/calls/')
        self.assertEqual(response.status_code, 401)

    def test_unauthenticated_cannot_create_room(self):
        response = self.client.post('/api/calls/', {
            'room_name': 'New Interview',
            'meeting_date': (timezone.now() + timedelta(hours=2)).isoformat(),
        })
        self.assertEqual(response.status_code, 401)

    def test_authenticated_user_can_list_rooms(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.get('/api/calls/')
        self.assertEqual(response.status_code, 200)

    def test_list_includes_rooms_where_user_is_host(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.get('/api/calls/')
        ids = [r['id'] for r in response.data]
        self.assertIn(self.room.id, ids)

    def test_list_includes_rooms_where_user_is_participant(self):
        self.room.participants.add(self.candidate)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.get('/api/calls/')
        ids = [r['id'] for r in response.data]
        self.assertIn(self.room.id, ids)

    def test_list_excludes_rooms_where_user_is_neither_host_nor_participant(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer2_token.key)
        response = self.client.get('/api/calls/')
        ids = [r['id'] for r in response.data]
        self.assertNotIn(self.room.id, ids)

    def test_list_excludes_expired_rooms_with_meeting_date(self):
        expired = Room.objects.create(
            room_name='Expired Room',
            host=self.employer1,
            meeting_date=timezone.now() - timedelta(hours=25),
        )
        expired.participants.add(self.employer1)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.get('/api/calls/')
        ids = [r['id'] for r in response.data]
        self.assertNotIn(expired.id, ids)

    def test_list_excludes_old_rooms_without_meeting_date(self):
        old = Room.objects.create(
            room_name='Old Room',
            host=self.employer1,
        )
        old.participants.add(self.employer1)
        Room.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(hours=25)
        )
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.get('/api/calls/')
        ids = [r['id'] for r in response.data]
        self.assertNotIn(old.id, ids)

    def test_employer_can_create_room(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.post('/api/calls/', {
            'room_name': 'New Interview',
            'meeting_date': (timezone.now() + timedelta(hours=2)).isoformat(),
            'description': 'Technical round',
        })
        self.assertEqual(response.status_code, 201)

    def test_candidate_cannot_create_room(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.post('/api/calls/', {
            'room_name': 'New Interview',
            'meeting_date': (timezone.now() + timedelta(hours=2)).isoformat(),
        })
        self.assertEqual(response.status_code, 403)

    def test_create_room_missing_name_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.post('/api/calls/', {'room_name': ''})
        self.assertEqual(response.status_code, 400)

    def test_cannot_create_room_with_past_meeting_date(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.post('/api/calls/', {
            'room_name': 'Bad Room',
            'meeting_date': (timezone.now() - timedelta(hours=1)).isoformat(),
        })
        self.assertEqual(response.status_code, 400)

    def test_host_is_set_automatically_on_create(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.post('/api/calls/', {
            'room_name': 'Auto Host Room',
            'meeting_date': (timezone.now() + timedelta(hours=2)).isoformat(),
        })
        self.assertEqual(response.status_code, 201)
        room = Room.objects.get(id=response.data['id'])
        self.assertEqual(room.host, self.employer1)

    def test_host_is_added_as_participant_on_create(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.post('/api/calls/', {
            'room_name': 'Participant Room',
            'meeting_date': (timezone.now() + timedelta(hours=2)).isoformat(),
        })
        self.assertEqual(response.status_code, 201)
        room = Room.objects.get(id=response.data['id'])
        self.assertIn(self.employer1, room.participants.all())

    def test_employer_can_create_room_without_meeting_date(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.post('/api/calls/', {
            'room_name': 'Instant Room',
            'description': 'No scheduled time',
        })
        self.assertEqual(response.status_code, 201)
        room = Room.objects.get(id=response.data['id'])
        self.assertIsNone(room.meeting_date)

class RoomDetailViewTests(TestCase):

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

    def test_authenticated_user_can_retrieve_room(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.get(f'/api/calls/{self.room.id}/')
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_cannot_retrieve_room(self):
        response = self.client.get(f'/api/calls/{self.room.id}/')
        self.assertEqual(response.status_code, 401)

    def test_nonexistent_room_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.get('/api/calls/99999/')
        self.assertEqual(response.status_code, 404)

    def test_host_can_update_room(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.patch(f'/api/calls/{self.room.id}/', {'room_name': 'Updated Room'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['room_name'], 'Updated Room')

    def test_non_host_employer_cannot_update_room(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer2_token.key)
        response = self.client.patch(f'/api/calls/{self.room.id}/', {'room_name': 'Hacked'})
        self.assertEqual(response.status_code, 403)

    def test_candidate_cannot_update_room(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.patch(f'/api/calls/{self.room.id}/', {'room_name': 'Hacked'})
        self.assertEqual(response.status_code, 403)

    def test_host_can_delete_room(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.delete(f'/api/calls/{self.room.id}/')
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Room.objects.filter(pk=self.room.id).exists())

    def test_non_host_employer_cannot_delete_room(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer2_token.key)
        response = self.client.delete(f'/api/calls/{self.room.id}/')
        self.assertEqual(response.status_code, 403)

    def test_candidate_cannot_delete_room(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.delete(f'/api/calls/{self.room.id}/')
        self.assertEqual(response.status_code, 403)

    def test_host_can_full_update_room(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.put(f'/api/calls/{self.room.id}/', {
            'room_name': 'Fully Updated Room',
            'description': 'New description',
            'meeting_date': (timezone.now() + timedelta(hours=3)).isoformat(),
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['room_name'], 'Fully Updated Room')

class RoomParticipantViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.employer = User.objects.create_user(
            username='employer1', password='password', role=User.Role.EMPLOYER
        )
        EmployerProfile.objects.create(user=self.employer, company_name='Company One')
        self.employer_token = Token.objects.create(user=self.employer)

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
            host=self.employer,
            meeting_date=timezone.now() + timedelta(hours=1),
        )
        self.room.participants.add(self.employer)

    def test_unauthenticated_cannot_add_participant(self):
        response = self.client.post(
            f'/api/calls/{self.room.id}/participants/',
            {'user_id': self.candidate.id}
        )
        self.assertEqual(response.status_code, 401)

    def test_host_can_add_participant_by_user_id(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer_token.key)
        response = self.client.post(
            f'/api/calls/{self.room.id}/participants/',
            {'user_id': self.candidate.id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'added')
        self.assertIn(self.candidate, self.room.participants.all())

    def test_non_host_cannot_add_participant(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer2_token.key)
        response = self.client.post(
            f'/api/calls/{self.room.id}/participants/',
            {'user_id': self.candidate.id}
        )
        self.assertEqual(response.status_code, 403)

    def test_candidate_cannot_add_participant(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.post(
            f'/api/calls/{self.room.id}/participants/',
            {'user_id': self.candidate.id}
        )
        self.assertEqual(response.status_code, 403)

    def test_add_participant_missing_user_id_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer_token.key)
        response = self.client.post(f'/api/calls/{self.room.id}/participants/', {})
        self.assertEqual(response.status_code, 400)

    def test_add_participant_nonexistent_user_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer_token.key)
        response = self.client.post(
            f'/api/calls/{self.room.id}/participants/',
            {'user_id': 99999}
        )
        self.assertEqual(response.status_code, 404)

    def test_add_participant_nonexistent_room_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer_token.key)
        response = self.client.post(
            '/api/calls/99999/participants/',
            {'user_id': self.candidate.id}
        )
        self.assertEqual(response.status_code, 404)

    def test_user_can_remove_themselves(self):
        self.room.participants.add(self.candidate)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.delete(f'/api/calls/{self.room.id}/participants/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'removed')
        self.assertNotIn(self.candidate, self.room.participants.all())

    def test_unauthenticated_cannot_remove_participant(self):
        response = self.client.delete(f'/api/calls/{self.room.id}/participants/')
        self.assertEqual(response.status_code, 401)

    def test_host_can_remove_themselves(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer_token.key)
        response = self.client.delete(f'/api/calls/{self.room.id}/participants/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'removed')
        self.assertNotIn(self.employer, self.room.participants.all())

    def test_remove_participant_nonexistent_room_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.delete('/api/calls/99999/participants/')
        self.assertEqual(response.status_code, 404)

class RoomTokenViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.employer = User.objects.create_user(
            username='employer1', password='password', role=User.Role.EMPLOYER
        )
        EmployerProfile.objects.create(user=self.employer, company_name='Company One')
        self.employer_token = Token.objects.create(user=self.employer)

        self.candidate = User.objects.create_user(
            username='candidate1', password='password', role=User.Role.CANDIDATE
        )
        CandidateProfile.objects.create(user=self.candidate)
        self.candidate_token = Token.objects.create(user=self.candidate)

        # Active room: meeting started 5 minutes ago
        self.active_room = Room.objects.create(
            room_name='Active Room',
            host=self.employer,
            meeting_date=timezone.now() - timedelta(minutes=5),
        )
        self.active_room.participants.add(self.employer)
        self.active_room.participants.add(self.candidate)

        # Future room: meeting hasn't started yet
        self.future_room = Room.objects.create(
            room_name='Future Room',
            host=self.employer,
            meeting_date=timezone.now() + timedelta(hours=2),
        )
        self.future_room.participants.add(self.employer)
        self.future_room.participants.add(self.candidate)

        # Expired room: meeting was more than 24 hours ago
        self.expired_room = Room.objects.create(
            room_name='Expired Room',
            host=self.employer,
            meeting_date=timezone.now() - timedelta(hours=25),
        )
        self.expired_room.participants.add(self.employer)
        self.expired_room.participants.add(self.candidate)

    def test_unauthenticated_cannot_get_token(self):
        response = self.client.post(f'/api/calls/{self.active_room.id}/token/')
        self.assertEqual(response.status_code, 401)

    def test_token_for_nonexistent_room_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.post('/api/calls/99999/token/')
        self.assertEqual(response.status_code, 404)

    def test_non_participant_cannot_get_token(self):
        outsider = User.objects.create_user(
            username='outsider', password='password', role=User.Role.CANDIDATE
        )
        CandidateProfile.objects.create(user=outsider)
        outsider_token = Token.objects.create(user=outsider)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + outsider_token.key)
        response = self.client.post(f'/api/calls/{self.active_room.id}/token/')
        self.assertEqual(response.status_code, 403)

    def test_cannot_get_token_before_meeting_starts(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.post(f'/api/calls/{self.future_room.id}/token/')
        self.assertEqual(response.status_code, 400)

    def test_cannot_get_token_for_expired_meeting(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.post(f'/api/calls/{self.expired_room.id}/token/')
        self.assertEqual(response.status_code, 400)

    @patch('calls.views.livekit_api.AccessToken')
    def test_participant_can_get_token(self, mock_token_class):
        mock_token = MagicMock()
        mock_token.to_jwt.return_value = 'fake-jwt-token'
        mock_token_class.return_value = mock_token

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.post(f'/api/calls/{self.active_room.id}/token/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.data)
        self.assertIn('url', response.data)
        self.assertIn('room_name', response.data)
        self.assertFalse(response.data['is_host'])

    @patch('calls.views.livekit_api.AccessToken')
    def test_host_token_has_is_host_true(self, mock_token_class):
        mock_token = MagicMock()
        mock_token.to_jwt.return_value = 'fake-jwt-token'
        mock_token_class.return_value = mock_token

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer_token.key)
        response = self.client.post(f'/api/calls/{self.active_room.id}/token/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['is_host'])

    @patch('calls.views.livekit_api.AccessToken')
    def test_room_name_in_token_response_matches_room_id(self, mock_token_class):
        mock_token = MagicMock()
        mock_token.to_jwt.return_value = 'fake-jwt-token'
        mock_token_class.return_value = mock_token

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer_token.key)
        response = self.client.post(f'/api/calls/{self.active_room.id}/token/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['room_name'], str(self.active_room.id))

    @patch('calls.views.livekit_api.AccessToken')
    def test_participant_can_get_token_for_room_without_meeting_date(self, mock_token_class):
        mock_token = MagicMock()
        mock_token.to_jwt.return_value = 'fake-jwt-token'
        mock_token_class.return_value = mock_token

        dateless_room = Room.objects.create(
            room_name='Dateless Room',
            host=self.employer,
        )
        dateless_room.participants.add(self.employer)
        dateless_room.participants.add(self.candidate)

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.post(f'/api/calls/{dateless_room.id}/token/')
        self.assertEqual(response.status_code, 200)

    @patch('calls.views.livekit_api.AccessToken')
    def test_token_response_contains_correct_livekit_url(self, mock_token_class):
        mock_token = MagicMock()
        mock_token.to_jwt.return_value = 'fake-jwt-token'
        mock_token_class.return_value = mock_token

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.post(f'/api/calls/{self.active_room.id}/token/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['url'], 'ws://localhost:7880')

class DeleteExpiredRoomsTaskTests(TestCase):

    def setUp(self):
        self.employer = User.objects.create_user(
            username='employer1', password='password', role=User.Role.EMPLOYER
        )
        EmployerProfile.objects.create(user=self.employer, company_name='Company One')

    def test_deletes_rooms_with_expired_meeting_date(self):
        from calls.tasks import delete_expired_rooms
        expired = Room.objects.create(
            room_name='Expired',
            host=self.employer,
            meeting_date=timezone.now() - timedelta(hours=25),
        )
        delete_expired_rooms()
        self.assertFalse(Room.objects.filter(pk=expired.pk).exists())

    def test_deletes_rooms_without_meeting_date_past_expiry(self):
        from calls.tasks import delete_expired_rooms
        old = Room.objects.create(
            room_name='Old',
            host=self.employer,
        )
        Room.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(hours=25)
        )
        delete_expired_rooms()
        self.assertFalse(Room.objects.filter(pk=old.pk).exists())

    def test_does_not_delete_active_rooms_with_future_meeting_date(self):
        from calls.tasks import delete_expired_rooms
        active = Room.objects.create(
            room_name='Active',
            host=self.employer,
            meeting_date=timezone.now() + timedelta(hours=2),
        )
        delete_expired_rooms()
        self.assertTrue(Room.objects.filter(pk=active.pk).exists())

    def test_does_not_delete_recent_rooms_without_meeting_date(self):
        from calls.tasks import delete_expired_rooms
        recent = Room.objects.create(
            room_name='Recent',
            host=self.employer,
        )
        delete_expired_rooms()
        self.assertTrue(Room.objects.filter(pk=recent.pk).exists())
