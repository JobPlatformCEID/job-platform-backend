from unittest.mock import patch, MagicMock, AsyncMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer
import json
 
from .models import InterviewSession, InterviewMessage
from .tasks import (
    get_history, append_to_history, compress_history,
    invalidate_history, generate_ai_response,
    HISTORY_KEY, SUMMARY_KEY,
)
from .services import (
    get_system_prompt, build_messages, get_ai_response,
    get_opening_message, summarize_history, SUMMARY_THRESHOLD,
)
 
User = get_user_model()

class InterviewSessionModelTest(TestCase):
 
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass')
        self.session = InterviewSession.objects.create(user=self.user, job_role='QA Engineer')

    def test_session_str(self):
        session = InterviewSession.objects.create(user=self.user, job_role='Backend Engineer')
        self.assertIn('Backend Engineer', str(session))
 
    def test_session_default_title(self):
        session = InterviewSession.objects.create(user=self.user, job_role='Designer')
        self.assertEqual(session.title, '')
 
    def test_session_ordering_newest_first(self):
        s1 = InterviewSession.objects.create(user=self.user, job_role='Role A')
        s2 = InterviewSession.objects.create(user=self.user, job_role='Role B')
        sessions = list(InterviewSession.objects.filter(user=self.user))
        self.assertEqual(sessions[0], s2)
        self.assertEqual(sessions[1], s1)

    def test_message_str_truncates(self):
        msg = InterviewMessage.objects.create(
            session=self.session,
            role=InterviewMessage.Role.USER,
            content='A' * 100,
        )
        self.assertLessEqual(len(str(msg)), 60)

    def test_message_role_choices(self):
        user_msg = InterviewMessage.objects.create(
            session=self.session, role=InterviewMessage.Role.USER, content='hi'
        )
        ai_msg = InterviewMessage.objects.create(
            session=self.session, role=InterviewMessage.Role.Assistant, content='hello'
        )
        self.assertEqual(user_msg.role, 'user')
        self.assertEqual(ai_msg.role, 'assistant')
 
    def test_messages_ordered_by_created_at(self):
        m1 = InterviewMessage.objects.create(session=self.session, role='user', content='first')
        m2 = InterviewMessage.objects.create(session=self.session, role='assistant', content='second')
        messages = list(self.session.messages.all())
        self.assertEqual(messages[0], m1)
        self.assertEqual(messages[1], m2)
 
    
class InterviewSessionListCreateViewTest(APITestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass')
        self.other_user = User.objects.create_user(username='bob', password='pass')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = '/api/sessions/'
 
    def test_create_session_creates_opening_message(self):
        response = self.client.post(self.url, {'job_role': 'Data Scientist', 'title': 'Test'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session_id = response.data['id']
        msgs = InterviewMessage.objects.filter(session_id=session_id)
        self.assertEqual(msgs.count(), 1)
        self.assertEqual(msgs.first().role, InterviewMessage.Role.Assistant)
 
    def test_list_returns_only_own_sessions(self):
        InterviewSession.objects.create(user=self.user, job_role='Dev')
        InterviewSession.objects.create(user=self.other_user, job_role='Manager')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
 
    def test_unauthenticated_request_is_rejected(self):
        client = APIClient()
        response = client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
 
 
class InterviewSessionDetailViewTest(APITestCase):
 
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass')
        self.other_user = User.objects.create_user(username='bob', password='pass')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.session = InterviewSession.objects.create(user=self.user, job_role='DevOps')
 
    def _url(self, pk):
        return f'/api/sessions/{pk}/'
 
    def test_retrieve_own_session(self):
        response = self.client.get(self._url(self.session.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
 
    def test_cannot_retrieve_other_users_session(self):
        other_session = InterviewSession.objects.create(user=self.other_user, job_role='PM')
        response = self.client.get(self._url(other_session.pk))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
 
    def test_delete_own_session(self):
        response = self.client.delete(self._url(self.session.pk))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(InterviewSession.objects.filter(pk=self.session.pk).exists())
 
    def test_cannot_delete_other_users_session(self):
        other_session = InterviewSession.objects.create(user=self.other_user, job_role='PM')
        response = self.client.delete(self._url(other_session.pk))
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])
 
 
class MessageListCreateViewTest(APITestCase):
 
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.session = InterviewSession.objects.create(user=self.user, job_role='SRE')
 
    def _url(self):
        return f'/api/sessions/{self.session.pk}/messages/'
 
    def test_create_message_saves_user_message(self):
        response = self.client.post(self._url(), {'content': 'Tell me about yourself'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['role'], InterviewMessage.Role.USER)
 
    def test_create_message_empty_content_returns_400(self):
        response = self.client.post(self._url(), {'content': ''})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
 
    def test_create_message_missing_content_returns_400(self):
        response = self.client.post(self._url(), {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
 
    def test_list_messages_only_from_own_session(self):
        InterviewMessage.objects.create(session=self.session, role='user', content='hello')
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
 
    def test_cannot_post_to_another_users_session(self):
        other_user = User.objects.create_user(username='bob', password='pass')
        other_session = InterviewSession.objects.create(user=other_user, job_role='Analyst')
        url = f'/api/interviews/{other_session.pk}/messages/'
        response = self.client.post(url, {'content': 'sneaky message'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)