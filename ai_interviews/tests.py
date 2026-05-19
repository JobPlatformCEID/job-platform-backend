from itertools import count
from unittest.mock import patch, MagicMock, AsyncMock, call

from django.test import TestCase
from django.core.cache import cache
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from channels.testing import WebsocketCommunicator
import logging

from .models import InterviewSession, InterviewMessage
from .serializers import (
    MessageSerializer,
    InterviewSessionSerializer,
    InterviewSessionDetailSerializer,
)
from .tasks import (
    get_history,
    append_to_history,
    compress_history,
    invalidate_history,
    generate_ai_response,
    generate_opening_message,
    HISTORY_KEY,
    SUMMARY_KEY,
)
from .services import (
    get_system_prompt,
    build_messages,
    get_ai_response,
    get_opening_message,
    summarize_history,
    SUMMARY_THRESHOLD,
)

from django.contrib.auth import get_user_model
from jobs.models import JobPosting
from users.models import EmployerProfile

User = get_user_model()
_employer_counter = count(1)

def make_employer_user():
    n = next(_employer_counter)
    user = User.objects.create_user(
        username=f"employer_{n}",
        password="pass",
        role=User.Role.EMPLOYER,
    )
    EmployerProfile.objects.create(user=user, company_name=f"Company {n}")
    return user


def create_test_job(
    title="Backend Engineer",
    description="Build backend systems.",
    requirements="Python, Django",
):
    employer_user = make_employer_user()
    return JobPosting.objects.create(
        employer=employer_user.employer_profile,
        title=title,
        description=description,
        requirements=requirements,
        contract_type="full_time",
    )


def make_session(user, title=""):
    job = create_test_job()
    return InterviewSession.objects.create(user=user, job_posting=job, title=title)


def make_user(username="testuser"):
    return User.objects.create_user(username=username, password="pass")

class InterviewSessionModelTest(TestCase):

    def setUp(self):
        self.user = make_user("model_user")
        self.job = create_test_job("QA Engineer")
        self.session = InterviewSession.objects.create(user=self.user, job_posting=self.job)

    def test_str_contains_job_title(self):
        self.assertIn("QA Engineer", str(self.session))

    def test_default_title_is_empty_string(self):
        self.assertEqual(self.session.title, "")

    def test_custom_title_is_stored(self):
        self.session.title = "My Interview"
        self.session.save()
        self.assertEqual(InterviewSession.objects.get(pk=self.session.pk).title, "My Interview")

    def test_sessions_ordered_newest_first(self):
        job2 = create_test_job("Role B")
        job3 = create_test_job("Role C")
        s1 = InterviewSession.objects.create(user=self.user, job_posting=job2)
        s2 = InterviewSession.objects.create(user=self.user, job_posting=job3)
        ordered = list(InterviewSession.objects.filter(user=self.user))
        self.assertEqual(ordered[0], s2)
        self.assertEqual(ordered[1], s1)

    def test_cascade_delete_removes_messages(self):
        InterviewMessage.objects.create(
            session=self.session, role=InterviewMessage.Role.USER, content="hi"
        )
        self.session.delete()
        self.assertEqual(InterviewMessage.objects.count(), 0)


class InterviewMessageModelTest(TestCase):

    def setUp(self):
        self.user = make_user("msg_model_user")
        self.session = make_session(self.user)

    def test_role_choices_user(self):
        msg = InterviewMessage.objects.create(
            session=self.session, role=InterviewMessage.Role.USER, content="hello"
        )
        self.assertEqual(msg.role, "user")

    def test_role_choices_assistant(self):
        msg = InterviewMessage.objects.create(
            session=self.session, role=InterviewMessage.Role.Assistant, content="hello"
        )
        self.assertEqual(msg.role, "assistant")

    def test_str_truncates_to_60_chars(self):
        msg = InterviewMessage.objects.create(
            session=self.session, role=InterviewMessage.Role.USER, content="A" * 100
        )
        self.assertLessEqual(len(str(msg)), 60)

    def test_messages_ordered_by_created_at_ascending(self):
        m1 = InterviewMessage.objects.create(
            session=self.session, role="user", content="first"
        )
        m2 = InterviewMessage.objects.create(
            session=self.session, role="assistant", content="second"
        )
        msgs = list(self.session.messages.all())
        self.assertEqual(msgs[0], m1)
        self.assertEqual(msgs[1], m2)

class MessageSerializerTest(TestCase):

    def setUp(self):
        self.user = make_user("ser_user")
        self.session = make_session(self.user)
        self.msg = InterviewMessage.objects.create(
            session=self.session, role="user", content="hello"
        )

    def test_serializer_fields(self):
        data = MessageSerializer(self.msg).data
        self.assertIn("id", data)
        self.assertIn("role", data)
        self.assertIn("content", data)
        self.assertIn("created_at", data)

    def test_id_and_created_at_are_read_only(self):
        serializer = MessageSerializer(data={"id": 999, "role": "user", "content": "x", "created_at": "2020-01-01"})
        serializer.is_valid()
        # read_only fields should not appear in validated_data
        self.assertNotIn("id", serializer.validated_data)
        self.assertNotIn("created_at", serializer.validated_data)


class InterviewSessionSerializerTest(TestCase):

    def setUp(self):
        self.user = make_user("sess_ser_user")
        self.job = create_test_job("Data Scientist")

    def test_create_with_job_posting_id(self):
        serializer = InterviewSessionSerializer(data={"job_posting_id": self.job.id})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_job_posting_id_is_write_only(self):
        serializer = InterviewSessionSerializer(data={"job_posting_id": self.job.id})
        serializer.is_valid()
        session = serializer.save(user=self.user)
        output = InterviewSessionSerializer(session).data
        self.assertNotIn("job_posting_id", output)
        self.assertIn("job_posting", output)

    def test_job_title_is_present(self):
        serializer = InterviewSessionSerializer(data={"job_posting_id": self.job.id})
        serializer.is_valid()
        session = serializer.save(user=self.user)
        output = InterviewSessionSerializer(session).data
        self.assertEqual(output["job_title"], "Data Scientist")

class InterviewSessionDetailSerializerTest(TestCase):

    def setUp(self):
        self.user = make_user("detail_ser_user")
        self.session = make_session(self.user)
        InterviewMessage.objects.create(
            session=self.session, role="user", content="first message"
        )

    def test_messages_nested_in_detail_serializer(self):
        data = InterviewSessionDetailSerializer(self.session).data
        self.assertIn("messages", data)
        self.assertEqual(len(data["messages"]), 1)
        self.assertEqual(data["messages"][0]["content"], "first message")

    def test_job_posting_is_read_only(self):
        data = InterviewSessionDetailSerializer(self.session).data
        self.assertIn("job_posting", data)

class SessionListCreateViewTest(APITestCase):

    def setUp(self):
        self.user = make_user("lc_user")
        self.other = make_user("lc_other")
        self.client.force_authenticate(user=self.user)
        self.url = "/api/sessions/"

    def test_unauthenticated_gets_401(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_returns_only_own_sessions(self):
        make_session(self.user)
        make_session(self.other)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    @patch("ai_interviews.views.generate_opening_message")
    def test_create_session_returns_201(self, mock_task):
        job = create_test_job("ML Eng")
        response = self.client.post(self.url, {"job_posting_id": job.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch("ai_interviews.views.generate_opening_message")
    def test_create_dispatches_opening_message_task(self, mock_task):
        job = create_test_job("SRE")
        response = self.client.post(self.url, {"job_posting_id": job.id})
        session_id = response.data["id"]
        mock_task.delay.assert_called_once_with(
            session_id, f"interview_session_{session_id}"
        )

    @patch("ai_interviews.views.generate_opening_message")
    def test_create_does_not_synchronously_create_message(self, mock_task):
        job = create_test_job("Infra Eng")
        response = self.client.post(self.url, {"job_posting_id": job.id})
        session_id = response.data["id"]
        self.assertEqual(InterviewMessage.objects.filter(session_id=session_id).count(), 0)

    def test_create_without_job_posting_id_returns_400(self):
        with patch("ai_interviews.views.generate_opening_message"):
            response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class SessionDetailViewTest(APITestCase):

    def setUp(self):
        self.user = make_user("detail_user")
        self.other = make_user("detail_other")
        self.client.force_authenticate(user=self.user)
        self.session = make_session(self.user)

    def _url(self, pk=None):
        return f"/api/sessions/{pk or self.session.pk}/"

    def test_retrieve_own_session_returns_200(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_includes_messages(self):
        InterviewMessage.objects.create(
            session=self.session, role="user", content="hello"
        )
        response = self.client.get(self._url())
        self.assertIn("messages", response.data)
        self.assertEqual(len(response.data["messages"]), 1)

    def test_cannot_retrieve_other_users_session(self):
        other_session = make_session(self.other)
        response = self.client.get(self._url(other_session.pk))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_title_returns_200(self):
        response = self.client.patch(self._url(), {"title": "Updated Title"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.session.refresh_from_db()
        self.assertEqual(self.session.title, "Updated Title")

    def test_delete_own_session_returns_204(self):
        response = self.client.delete(self._url())
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(InterviewSession.objects.filter(pk=self.session.pk).exists())

    def test_cannot_delete_other_users_session(self):
        other_session = make_session(self.other)
        response = self.client.delete(self._url(other_session.pk))
        self.assertIn(
            response.status_code,
            [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND],
        )

    def test_unauthenticated_cannot_access(self):
        self.client.logout()
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class MessageListCreateViewTest(APITestCase):

    def setUp(self):
        self.user = make_user("msg_view_user")
        self.client.force_authenticate(user=self.user)
        self.session = make_session(self.user)

    def _url(self, session_pk=None):
        pk = session_pk or self.session.pk
        return f"/api/sessions/{pk}/messages/"

    def test_list_returns_messages_for_own_session(self):
        InterviewMessage.objects.create(
            session=self.session, role="user", content="hello"
        )
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_message_returns_201_with_user_role(self):
        response = self.client.post(self._url(), {"content": "Tell me about yourself"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["role"], "user")

    def test_create_message_saves_to_db(self):
        self.client.post(self._url(), {"content": "What is the stack?"})
        self.assertEqual(
            InterviewMessage.objects.filter(session=self.session).count(), 1
        )

    def test_empty_content_returns_400(self):
        response = self.client.post(self._url(), {"content": ""})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_content_returns_400(self):
        response = self.client.post(self._url(), {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_post_to_other_users_session(self):
        other = make_user("other_msg_user")
        other_session = make_session(other)
        response = self.client.post(
            self._url(other_session.pk), {"content": "sneaky"}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_cannot_list(self):
        self.client.logout()
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RedisTests(TestCase):

    def setUp(self):
        self.user = make_user("redis_user")
        self.session = make_session(self.user)
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_returns_cached_history_on_cache_hit(self):
        key = HISTORY_KEY.format(self.session.id)
        cached = [{"role": "user", "content": "cached message"}]
        cache.set(key, cached, timeout=3600)
        result = get_history(self.session.id)
        self.assertEqual(result, cached)

    def test_falls_back_to_db_on_cache_miss(self):
        InterviewMessage.objects.create(
            session=self.session, role="user", content="from db"
        )
        result = get_history(self.session.id)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["content"], "from db")

    def test_db_fallback_populates_cache(self):
        InterviewMessage.objects.create(
            session=self.session, role="user", content="populate"
        )
        get_history(self.session.id)
        cached = cache.get(HISTORY_KEY.format(self.session.id))
        self.assertIsNotNone(cached)
        self.assertEqual(cached[0]["content"], "populate")

    def test_empty_db_returns_empty_list(self):
        result = get_history(self.session.id)
        self.assertEqual(result, [])

    def test_db_fallback_respects_summary_threshold_limit(self):
        # Create more messages than SUMMARY_THRESHOLD; should only load the most recent ones
        for i in range(SUMMARY_THRESHOLD + 5):
            InterviewMessage.objects.create(
                session=self.session, role="user", content=f"msg {i}"
            )
        result = get_history(self.session.id)
        self.assertLessEqual(len(result), SUMMARY_THRESHOLD)

    def test_append_adds_message_to_existing_history(self):
        key = HISTORY_KEY.format(self.session.id)
        cache.set(key, [{"role": "user", "content": "first"}], timeout=3600)
        length = append_to_history(self.session.id, "assistant", "second")
        self.assertEqual(length, 2)

    def test_append_creates_new_history_when_cache_empty(self):
        length = append_to_history(self.session.id, "user", "hello")
        self.assertEqual(length, 1)

    def test_append_message_is_persisted_in_cache(self):
        append_to_history(self.session.id, "user", "test message")
        history = cache.get(HISTORY_KEY.format(self.session.id))
        self.assertEqual(history[0]["content"], "test message")
        self.assertEqual(history[0]["role"], "user")

    @patch("ai_interviews.tasks.summarize_history")
    def test_compress_returns_summary_plus_last_four_messages(self, mock_summarize):
        mock_summarize.return_value = "Here is the summary."
        history = [{"role": "user", "content": f"msg {i}"} for i in range(10)]
        result = compress_history(self.session, history)
        # 1 system summary message + 4 recent messages = 5
        self.assertEqual(len(result), 5)
        self.assertEqual(result[0]["role"], "system")
        self.assertIn("Here is the summary.", result[0]["content"])
        self.assertEqual(result[1:], history[-4:])

    @patch("ai_interviews.tasks.summarize_history")
    def test_compress_stores_summary_string_in_cache(self, mock_summarize):
        mock_summarize.return_value = "Summary text."
        history = [{"role": "user", "content": f"msg {i}"} for i in range(10)]
        compress_history(self.session, history)
        self.assertEqual(
            cache.get(SUMMARY_KEY.format(self.session.id)), "Summary text."
        )

    @patch("ai_interviews.tasks.summarize_history")
    def test_compress_replaces_history_in_cache(self, mock_summarize):
        mock_summarize.return_value = "summary"
        key = HISTORY_KEY.format(self.session.id)
        history = [{"role": "user", "content": f"msg {i}"} for i in range(10)]
        cache.set(key, history, timeout=3600)
        compress_history(self.session, history)
        updated = cache.get(key)
        self.assertIsNotNone(updated)
        self.assertEqual(len(updated), 5)

    def test_invalidate_clears_history_key(self):
        cache.set(HISTORY_KEY.format(self.session.id), [{"role": "user", "content": "hi"}])
        invalidate_history(self.session.id)
        self.assertIsNone(cache.get(HISTORY_KEY.format(self.session.id)))

    def test_invalidate_clears_summary_key(self):
        cache.set(SUMMARY_KEY.format(self.session.id), "old summary")
        invalidate_history(self.session.id)
        self.assertIsNone(cache.get(SUMMARY_KEY.format(self.session.id)))

    def test_invalidate_is_safe_when_keys_do_not_exist(self):
        # Should not raise even if nothing is cached
        try:
            invalidate_history(self.session.id)
        except Exception as exc:
            self.fail(f"invalidate_history raised an exception: {exc}")


class GenerateAiResponseTaskTest(TestCase):

    def setUp(self):
        self.user = make_user("task_user")
        self.session = make_session(self.user)
        cache.clear()

    def tearDown(self):
        cache.clear()

    @patch("ai_interviews.tasks.async_to_sync")
    @patch("ai_interviews.tasks.get_ai_response")
    @patch("ai_interviews.tasks.get_history")
    def test_saves_ai_message_to_db(self, mock_history, mock_ai, mock_async):
        mock_history.return_value = [{"role": "user", "content": "hello"}]
        mock_ai.return_value = "AI response text"
        mock_async.return_value = MagicMock()

        generate_ai_response(self.session.id, "interview_session_1")

        ai_msg = InterviewMessage.objects.filter(
            session=self.session, role=InterviewMessage.Role.Assistant
        ).last()
        self.assertIsNotNone(ai_msg)
        self.assertEqual(ai_msg.content, "AI response text")

    @patch("ai_interviews.tasks.async_to_sync")
    @patch("ai_interviews.tasks.get_ai_response")
    @patch("ai_interviews.tasks.get_history")
    def test_appends_ai_response_to_cache(self, mock_history, mock_ai, mock_async):
        mock_history.return_value = [{"role": "user", "content": "hello"}]
        mock_ai.return_value = "cached response"
        mock_async.return_value = MagicMock()

        generate_ai_response(self.session.id, "interview_session_1")

        history = cache.get(HISTORY_KEY.format(self.session.id))
        self.assertIsNotNone(history)
        self.assertEqual(history[-1]["content"], "cached response")

    @patch("ai_interviews.tasks.async_to_sync")
    @patch("ai_interviews.tasks.get_ai_response")
    @patch("ai_interviews.tasks.get_history")
    def test_pushes_message_to_websocket_group(self, mock_history, mock_ai, mock_async):
        mock_history.return_value = [{"role": "user", "content": "hello"}]
        mock_ai.return_value = "ws response"
        mock_channel_send = MagicMock()
        mock_async.return_value = mock_channel_send

        generate_ai_response(self.session.id, "my_group")

        mock_channel_send.assert_called_once()
        group_send_payload = mock_channel_send.call_args[0][1]
        self.assertEqual(group_send_payload["type"], "ai_message")
        self.assertEqual(group_send_payload["message"]["content"], "ws response")

    @patch("ai_interviews.tasks.async_to_sync")
    @patch("ai_interviews.tasks.get_ai_response")
    @patch("ai_interviews.tasks.get_history")
    def test_triggers_compress_when_history_at_threshold(
        self, mock_history, mock_ai, mock_async
    ):
        mock_history.return_value = [
            {"role": "user", "content": f"msg {i}"} for i in range(SUMMARY_THRESHOLD)
        ]
        mock_ai.return_value = "response"
        mock_async.return_value = MagicMock()

        with patch("ai_interviews.tasks.compress_history") as mock_compress:
            mock_compress.return_value = [{"role": "system", "content": "summary"}]
            generate_ai_response(self.session.id, "interview_session_1")
            mock_compress.assert_called_once()

    @patch("ai_interviews.tasks.async_to_sync")
    @patch("ai_interviews.tasks.get_history")
    def test_sends_error_to_websocket_after_max_retries(self, mock_history, mock_async):
        mock_history.side_effect = Exception("Unexpected error")
        mock_channel_send = MagicMock()
        mock_async.return_value = mock_channel_send

        with self.assertLogs("ai_interviews.tasks", level="ERROR"):  # captures instead of printing
            generate_ai_response.apply(args=[self.session.id, "interview_session_1"])

        mock_async.assert_called()
        payload = mock_channel_send.call_args[0][1]
        self.assertEqual(payload["type"], "error")

    @patch("ai_interviews.tasks.async_to_sync")
    @patch("ai_interviews.tasks.get_ai_response")
    @patch("ai_interviews.tasks.get_history")
    def test_nonexistent_session_id_does_not_raise(
        self, mock_history, mock_ai, mock_async
    ):
        mock_async.return_value = MagicMock()
        try:
            generate_ai_response.apply(args=[99999, "some_group"])
        except Exception as exc:
            self.fail(f"Task raised unexpectedly: {exc}")


class GenerateOpeningMessageTaskTest(TestCase):

    def setUp(self):
        self.user = make_user("opening_task_user")
        self.session = make_session(self.user)
        cache.clear()

    def tearDown(self):
        cache.clear()

    @patch("ai_interviews.tasks.async_to_sync")
    @patch("ai_interviews.tasks.get_opening_message")
    def test_saves_opening_message_to_db(self, mock_opening, mock_async):
        mock_opening.return_value = "Welcome to the interview!"
        mock_async.return_value = MagicMock()

        generate_opening_message(self.session.id, "interview_session_1")

        msg = InterviewMessage.objects.filter(
            session=self.session, role=InterviewMessage.Role.Assistant
        ).first()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.content, "Welcome to the interview!")

    @patch("ai_interviews.tasks.async_to_sync")
    @patch("ai_interviews.tasks.get_opening_message")
    def test_pushes_opening_message_to_websocket(self, mock_opening, mock_async):
        mock_opening.return_value = "Hello candidate!"
        mock_channel_send = MagicMock()
        mock_async.return_value = mock_channel_send

        generate_opening_message(self.session.id, "my_group")

        mock_channel_send.assert_called_once()
        payload = mock_channel_send.call_args[0][1]
        self.assertEqual(payload["type"], "ai_message")

    @patch("ai_interviews.tasks.async_to_sync")
    @patch("ai_interviews.tasks.get_opening_message")
    def test_appends_opening_message_to_cache(self, mock_opening, mock_async):
        mock_opening.return_value = "cached welcome"
        mock_async.return_value = MagicMock()

        generate_opening_message(self.session.id, "interview_session_1")

        history = cache.get(HISTORY_KEY.format(self.session.id))
        self.assertIsNotNone(history)
        self.assertEqual(history[-1]["content"], "cached welcome")

    @patch("ai_interviews.tasks.async_to_sync")
    @patch("ai_interviews.tasks.get_opening_message")
    def test_sends_error_to_websocket_after_max_retries(
        self, mock_opening, mock_async
    ):
        mock_opening.side_effect = Exception("AI down")
        mock_channel_send = MagicMock()
        mock_async.return_value = mock_channel_send

        generate_opening_message.apply(args=[self.session.id, "interview_session_1"])

        mock_async.assert_called()
        payload = mock_channel_send.call_args[0][1]
        self.assertEqual(payload["type"], "error")

class ServicesTest(TestCase):

    def setUp(self):
        self.user = make_user("svc_user")
        self.session = InterviewSession.objects.create(
            user=self.user,
            job_posting=create_test_job(
                "Cloud Architect",
                description="Design and operate cloud infrastructure.",
                requirements="AWS, Terraform, distributed systems",
            ),
        )

    def test_get_system_prompt_includes_job_title(self):
        prompt = get_system_prompt(self.session)
        self.assertIn("Cloud Architect", prompt)

    def test_get_system_prompt_includes_requirements(self):
        prompt = get_system_prompt(self.session)
        self.assertIn("AWS, Terraform, distributed systems", prompt)

    def test_get_system_prompt_includes_job_description(self):
        prompt = get_system_prompt(self.session)
        self.assertIn("cloud infrastructure", prompt)

    def test_build_messages_first_message_is_system(self):
        history = [{"role": "user", "content": "hello"}]
        messages = build_messages(self.session, history)
        self.assertEqual(messages[0]["role"], "system")

    def test_build_messages_history_appended_after_system(self):
        history = [{"role": "user", "content": "my question"}]
        messages = build_messages(self.session, history)
        contents = [m["content"] for m in messages]
        self.assertIn("my question", contents)

    def test_build_messages_length_is_history_plus_one_system(self):
        history = [
            {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "a1"},
        ]
        messages = build_messages(self.session, history)
        self.assertEqual(len(messages), 3)

    @patch("ai_interviews.services._groq_response")
    @patch("ai_interviews.services.settings")
    def test_get_ai_response_uses_groq_when_configured(
        self, mock_settings, mock_groq
    ):
        mock_settings.AI_BACKEND = "groq"
        mock_groq.return_value = "groq answer"
        result = get_ai_response(self.session, [{"role": "user", "content": "q"}])
        self.assertEqual(result, "groq answer")
        mock_groq.assert_called_once()

    @patch("ai_interviews.services._ollama_response")
    @patch("ai_interviews.services.settings")
    def test_get_ai_response_uses_ollama_as_fallback(
        self, mock_settings, mock_ollama
    ):
        mock_settings.AI_BACKEND = "ollama"
        mock_ollama.return_value = "local answer"
        result = get_ai_response(self.session, [{"role": "user", "content": "q"}])
        self.assertEqual(result, "local answer")
        mock_ollama.assert_called_once()

    @patch("ai_interviews.services._groq_response")
    @patch("ai_interviews.services.settings")
    def test_get_opening_message_calls_backend(self, mock_settings, mock_groq):
        mock_settings.AI_BACKEND = "groq"
        mock_groq.return_value = "Welcome!"
        result = get_opening_message(self.session)
        self.assertEqual(result, "Welcome!")

    @patch("ai_interviews.services._groq_response")
    @patch("ai_interviews.services.settings")
    def test_get_opening_message_passes_two_messages(self, mock_settings, mock_groq):
        mock_settings.AI_BACKEND = "groq"
        mock_groq.return_value = "Hi!"
        get_opening_message(self.session)
        called_messages = mock_groq.call_args[0][0]
        self.assertEqual(len(called_messages), 2)
        self.assertEqual(called_messages[0]["role"], "system")
        self.assertEqual(called_messages[1]["role"], "user")

    @patch("ai_interviews.services._groq_response")
    @patch("ai_interviews.services.settings")
    def test_summarize_history_returns_summary_string(
        self, mock_settings, mock_groq
    ):
        mock_settings.AI_BACKEND = "groq"
        mock_groq.return_value = "Summary here."
        history = [{"role": "user", "content": "lots of messages"}]
        result = summarize_history(self.session, history)
        self.assertEqual(result, "Summary here.")

    @patch("ai_interviews.services._groq_response")
    @patch("ai_interviews.services.settings")
    def test_summarize_history_appends_summary_prompt(
        self, mock_settings, mock_groq
    ):
        """summarize_history should append a summary request after the history."""
        mock_settings.AI_BACKEND = "groq"
        mock_groq.return_value = "summary"
        history = [{"role": "user", "content": "msg"}]
        summarize_history(self.session, history)
        called_messages = mock_groq.call_args[0][0]
        # system + history messages + summary prompt user message
        self.assertGreater(len(called_messages), len(history) + 1)


class InterviewConsumerTest(TestCase):

    def setUp(self):
        self.user = make_user("ws_user")
        self.session = make_session(self.user)

    async def _make_communicator(self, session_id=None, user=None):
        from .consumers import InterviewConsumer

        sid = session_id if session_id is not None else self.session.id
        u = user if user is not None else self.user
        communicator = WebsocketCommunicator(
            InterviewConsumer.as_asgi(),
            f"/ws/interview/{sid}/",
        )
        communicator.scope["user"] = u
        communicator.scope["url_route"] = {"kwargs": {"session_id": str(sid)}}
        return communicator

    async def test_connect_valid_session_and_owner_succeeds(self):
        comm = await self._make_communicator()
        connected, _ = await comm.connect()
        self.assertTrue(connected)
        await comm.disconnect()

    async def test_connect_nonexistent_session_closes_4404(self):
        comm = await self._make_communicator(session_id=99999)
        connected, code = await comm.connect()
        self.assertFalse(connected)
        self.assertEqual(code, 4404)

    async def test_connect_wrong_user_closes_4403(self):
        other = await User.objects.acreate(username="ws_other_user", password="pass")
        comm = await self._make_communicator(user=other)
        connected, code = await comm.connect()
        self.assertFalse(connected)
        self.assertEqual(code, 4403)

    async def test_connect_unauthenticated_user_closes_4403(self):
        from django.contrib.auth.models import AnonymousUser
        comm = await self._make_communicator(user=AnonymousUser())
        connected, code = await comm.connect()
        self.assertFalse(connected)
        self.assertEqual(code, 4403)

    async def test_empty_content_returns_error(self):
        comm = await self._make_communicator()
        await comm.connect()
        await comm.send_json_to({"content": ""})
        response = await comm.receive_json_from()
        self.assertEqual(response["type"], "error")
        await comm.disconnect()

    async def test_whitespace_only_content_returns_error(self):
        comm = await self._make_communicator()
        await comm.connect()
        await comm.send_json_to({"content": "   "})
        response = await comm.receive_json_from()
        self.assertEqual(response["type"], "error")
        await comm.disconnect()

    async def test_invalid_json_returns_error(self):
        comm = await self._make_communicator()
        await comm.connect()
        await comm.send_to(text_data="not json at all {{")
        response = await comm.receive_json_from()
        self.assertEqual(response["type"], "error")
        await comm.disconnect()

    @patch("ai_interviews.consumers.generate_ai_response")
    @patch("ai_interviews.consumers.append_to_history")
    async def test_valid_message_echoed_back_as_user_message(
        self, mock_append, mock_task
    ):
        mock_append.return_value = 1
        mock_task.delay = MagicMock()
        comm = await self._make_communicator()
        await comm.connect()
        await comm.send_json_to({"content": "Tell me about your experience."})
        response = await comm.receive_json_from()
        self.assertEqual(response["type"], "user_message")
        self.assertEqual(response["message"]["content"], "Tell me about your experience.")
        await comm.disconnect()

    @patch("ai_interviews.consumers.generate_ai_response")
    @patch("ai_interviews.consumers.append_to_history")
    async def test_valid_message_saved_to_db(self, mock_append, mock_task):
        mock_append.return_value = 1
        mock_task.delay = MagicMock()
        comm = await self._make_communicator()
        await comm.connect()
        await comm.send_json_to({"content": "What is the biggest challenge?"})
        await comm.receive_json_from()
        count = await InterviewMessage.objects.filter(
            session=self.session, role="user"
        ).acount()
        self.assertEqual(count, 1)
        await comm.disconnect()

    @patch("ai_interviews.consumers.generate_ai_response")
    @patch("ai_interviews.consumers.append_to_history")
    async def test_valid_message_triggers_celery_task(
        self, mock_append, mock_task
    ):
        mock_append.return_value = 1
        mock_task.delay = MagicMock()
        comm = await self._make_communicator()
        await comm.connect()
        await comm.send_json_to({"content": "What is the stack?"})
        await comm.receive_json_from()  # consume echo
        mock_task.delay.assert_called_once_with(
            str(self.session.id), f"interview_session_{self.session.id}"
        )
        await comm.disconnect()

    @patch("ai_interviews.consumers.generate_ai_response")
    @patch("ai_interviews.consumers.append_to_history")
    async def test_redis_failure_sends_error_and_does_not_dispatch_task(
        self, mock_append, mock_task
    ):
        mock_append.side_effect = Exception("Redis down")
        mock_task.delay = MagicMock()
        comm = await self._make_communicator()
        await comm.connect()
        await comm.send_json_to({"content": "Hello?"})
        response = await comm.receive_json_from()
        self.assertEqual(response["type"], "error")
        mock_task.delay.assert_not_called()
        await comm.disconnect()

    async def test_ai_message_handler_forwards_to_client(self):
        comm = await self._make_communicator()
        await comm.connect()

        # Simulate Celery pushing an ai_message via channel layer
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        group_name = f"interview_session_{self.session.id}"
        await channel_layer.group_send(
            group_name,
            {
                "type": "ai_message",
                "message": {
                    "id": 1,
                    "role": "assistant",
                    "content": "Here is my answer.",
                    "created_at": "2024-01-01T00:00:00",
                },
            },
        )
        response = await comm.receive_json_from()
        self.assertEqual(response["type"], "ai_message")
        self.assertEqual(response["message"]["content"], "Here is my answer.")
        await comm.disconnect()

    async def test_error_handler_forwards_to_client(self):
        comm = await self._make_communicator()
        await comm.connect()

        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        group_name = f"interview_session_{self.session.id}"
        await channel_layer.group_send(
            group_name,
            {"type": "error", "message": "Something went wrong."},
        )
        response = await comm.receive_json_from()
        self.assertEqual(response["type"], "error")
        self.assertEqual(response["message"], "Something went wrong.")
        await comm.disconnect()