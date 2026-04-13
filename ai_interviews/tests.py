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