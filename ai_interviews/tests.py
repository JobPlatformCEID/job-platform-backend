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

class RedisTests(TestCase):
 
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass')
        self.session = InterviewSession.objects.create(user=self.user, job_role='ML Engineer')
        cache.clear()
 
    def tearDown(self):
        cache.clear()
 
    def test_get_history_returns_from_cache_when_available(self):
        key = HISTORY_KEY.format(self.session.id)
        cached_history = [{'role': 'user', 'content': 'cached'}]
        cache.set(key, cached_history, timeout=3600)
        result = get_history(self.session.id)
        self.assertEqual(result, cached_history)
 
    def test_get_history_falls_back_to_db_on_cache_miss(self):
        InterviewMessage.objects.create(session=self.session, role='user', content='from db')
        result = get_history(self.session.id)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['content'], 'from db')
 
    def test_get_history_db_fallback_populates_cache(self):
        InterviewMessage.objects.create(session=self.session, role='user', content='populate me')
        get_history(self.session.id)
        self.assertIsNotNone(cache.get(HISTORY_KEY.format(self.session.id)))
 
    def test_get_history_empty_returns_empty_list(self):
        self.assertEqual(get_history(self.session.id), [])
 
    def test_append_adds_to_existing_history(self):
        key = HISTORY_KEY.format(self.session.id)
        cache.set(key, [{'role': 'user', 'content': 'first'}], timeout=3600)
        length = append_to_history(self.session.id, 'assistant', 'second')
        self.assertEqual(length, 2)
 
    def test_append_creates_history_when_none_exists(self):
        length = append_to_history(self.session.id, 'user', 'hello')
        self.assertEqual(length, 1)
 
    def test_append_persists_message_in_cache(self):
        append_to_history(self.session.id, 'user', 'test message')
        history = cache.get(HISTORY_KEY.format(self.session.id))
        self.assertEqual(history[0]['content'], 'test message')
 
    @patch('ai_interviews.tasks.summarize_history')
    def test_compress_replaces_history_with_summary_and_recent(self, mock_summarize):
        mock_summarize.return_value = 'This is a summary.'
        history = [{'role': 'user', 'content': f'msg {i}'} for i in range(10)]
        result = compress_history(self.session, history)
        # 1 summary system message + 4 recent messages
        self.assertEqual(len(result), 5)
        self.assertEqual(result[0]['role'], 'system')
 
    @patch('ai_interviews.tasks.summarize_history')
    def test_compress_stores_summary_in_cache(self, mock_summarize):
        mock_summarize.return_value = 'Summary text.'
        history = [{'role': 'user', 'content': f'msg {i}'} for i in range(10)]
        compress_history(self.session, history)
        self.assertEqual(cache.get(SUMMARY_KEY.format(self.session.id)), 'Summary text.')

 
    def test_invalidate_clears_both_history_and_summary_keys(self):
        cache.set(HISTORY_KEY.format(self.session.id), [{'role': 'user', 'content': 'hi'}])
        cache.set(SUMMARY_KEY.format(self.session.id), 'Some summary')
        invalidate_history(self.session.id)
        self.assertIsNone(cache.get(HISTORY_KEY.format(self.session.id)))
        self.assertIsNone(cache.get(SUMMARY_KEY.format(self.session.id)))
 
    @patch('ai_interviews.tasks.async_to_sync')
    @patch('ai_interviews.tasks.get_ai_response')
    @patch('ai_interviews.tasks.get_history')
    def test_generate_saves_ai_message_to_db(self, mock_history, mock_ai, mock_async):
        mock_history.return_value = [{'role': 'user', 'content': 'hello'}]
        mock_ai.return_value = 'AI response text'
        mock_async.return_value = MagicMock()
 
        generate_ai_response(self.session.id, 'interview_session_1')
 
        ai_msg = InterviewMessage.objects.filter(
            session=self.session, role=InterviewMessage.Role.Assistant
        ).last()
        self.assertIsNotNone(ai_msg)
        self.assertEqual(ai_msg.content, 'AI response text')
 
    @patch('ai_interviews.tasks.async_to_sync')
    @patch('ai_interviews.tasks.get_ai_response')
    @patch('ai_interviews.tasks.get_history')
    def test_generate_triggers_compression_when_threshold_reached(self, mock_history, mock_ai, mock_async):
        mock_history.return_value = [{'role': 'user', 'content': f'msg {i}'} for i in range(SUMMARY_THRESHOLD)]
        mock_ai.return_value = 'response'
        mock_async.return_value = MagicMock()
 
        with patch('ai_interviews.tasks.compress_history') as mock_compress:
            mock_compress.return_value = [{'role': 'system', 'content': 'summary'}]
            generate_ai_response(self.session.id, 'interview_session_1')
            mock_compress.assert_called_once()
 
    @patch('ai_interviews.tasks.async_to_sync')
    @patch('ai_interviews.tasks.get_history')
    def test_generate_sends_error_to_websocket_on_failure(self, mock_history, mock_async):
        mock_history.side_effect = Exception('Unexpected error')
        mock_channel_send = MagicMock()
        mock_async.return_value = mock_channel_send
 
        # apply() swallows the exception after retries — check the side effect instead
        generate_ai_response.apply(args=[self.session.id, 'interview_session_1'])
 
        # async_to_sync should have been called to push an error to the WebSocket
        mock_async.assert_called()
        # confirm the group_send payload contained an error type
        send_call_args = mock_channel_send.call_args[0][1]
        self.assertEqual(send_call_args['type'], 'error')

class ServicesTest(TestCase):
 
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass')
        self.session = InterviewSession.objects.create(user=self.user, job_role='Cloud Architect')
 
    def test_get_system_prompt_includes_job_role(self):
        prompt = get_system_prompt(self.session)
        self.assertIn('Cloud Architect', prompt)
 
    def test_build_messages_starts_with_system(self):
        history = [{'role': 'user', 'content': 'hello'}]
        messages = build_messages(self.session, history)
        self.assertEqual(messages[0]['role'], 'system')
 
    def test_build_messages_includes_history(self):
        history = [{'role': 'user', 'content': 'my question'}]
        messages = build_messages(self.session, history)
        contents = [m['content'] for m in messages]
        self.assertIn('my question', contents)
 
    @patch('ai_interviews.services._groq_response')
    @patch('ai_interviews.services.settings')
    def test_get_ai_response_uses_groq_when_configured(self, mock_settings, mock_groq):
        mock_settings.AI_BACKEND = 'groq'
        mock_groq.return_value = 'groq answer'
        history = [{'role': 'user', 'content': 'question'}]
        result = get_ai_response(self.session, history)
        self.assertEqual(result, 'groq answer')
        mock_groq.assert_called_once()
 
    @patch('ai_interviews.services._ollama_response')
    @patch('ai_interviews.services.settings')
    def test_get_ai_response_falls_back_to_ollama(self, mock_settings, mock_ollama):
        mock_settings.AI_BACKEND = 'ollama'
        mock_ollama.return_value = 'local answer'
        history = [{'role': 'user', 'content': 'question'}]
        result = get_ai_response(self.session, history)
        self.assertEqual(result, 'local answer')
        mock_ollama.assert_called_once()
 
    @patch('ai_interviews.services._groq_response')
    @patch('ai_interviews.services.settings')
    def test_get_opening_message_calls_backend(self, mock_settings, mock_groq):
        mock_settings.AI_BACKEND = 'groq'
        mock_groq.return_value = 'Welcome!'
        result = get_opening_message(self.session)
        self.assertEqual(result, 'Welcome!')
 
    @patch('ai_interviews.services._groq_response')
    @patch('ai_interviews.services.settings')
    def test_summarize_history_returns_summary(self, mock_settings, mock_groq):
        mock_settings.AI_BACKEND = 'groq'
        mock_groq.return_value = 'Summary here.'
        history = [{'role': 'user', 'content': 'lots of messages'}]
        result = summarize_history(self.session, history)
        self.assertEqual(result, 'Summary here.')


class InterviewConsumerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='wsuser', password='pass')
        self.session = InterviewSession.objects.create(user=self.user, job_role='iOS Dev')
 
    async def _make_communicator(self, session_id=None, user=None):
        from .consumers import InterviewConsumer
        sid = session_id or self.session.id
        u = user or self.user
        communicator = WebsocketCommunicator(
            InterviewConsumer.as_asgi(),
            f'/ws/interviews/{sid}/'
        )
        communicator.scope['user'] = u
        communicator.scope['url_route'] = {'kwargs': {'session_id': str(sid)}}
        return communicator
 
    async def test_connect_valid_session_and_user(self):
        communicator = await self._make_communicator()
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()
 
    async def test_connect_nonexistent_session_closes_4404(self):
        communicator = await self._make_communicator(session_id=99999)
        connected, code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(code, 4404)
 
    async def test_connect_wrong_user_closes_4403(self):
        other_user = await User.objects.acreate(username='other', password='pass')
        communicator = await self._make_communicator(user=other_user)
        connected, code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(code, 4403)
 
    async def test_send_empty_message_returns_error(self):
        communicator = await self._make_communicator()
        await communicator.connect()
        await communicator.send_json_to({'content': ''})
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'error')
        await communicator.disconnect()
 
    async def test_send_invalid_json_returns_error(self):
        communicator = await self._make_communicator()
        await communicator.connect()
        await communicator.send_to(text_data='not json at all')
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'error')
        await communicator.disconnect()
 
    @patch('ai_interviews.consumers.generate_ai_response')
    @patch('ai_interviews.consumers.append_to_history')
    async def test_valid_message_echoed_back_as_user_message(self, mock_append, mock_task):
        mock_append.return_value = 1
        mock_task.delay = MagicMock()
        communicator = await self._make_communicator()
        await communicator.connect()
        await communicator.send_json_to({'content': 'Tell me about your experience.'})
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'user_message')
        self.assertEqual(response['message']['content'], 'Tell me about your experience.')
        await communicator.disconnect()
 
    @patch('ai_interviews.consumers.generate_ai_response')
    @patch('ai_interviews.consumers.append_to_history')
    async def test_valid_message_triggers_celery_task(self, mock_append, mock_task):
        mock_append.return_value = 1
        mock_task.delay = MagicMock()
        communicator = await self._make_communicator()
        await communicator.connect()
        await communicator.send_json_to({'content': 'What is your biggest challenge?'})
        await communicator.receive_json_from()  # consume the user_message echo
        mock_task.delay.assert_called_once_with(str(self.session.id), f'interview_session_{self.session.id}')
        await communicator.disconnect()