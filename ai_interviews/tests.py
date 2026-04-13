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
 