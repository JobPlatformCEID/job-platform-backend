from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from users.models import User, EmployerProfile
from .models import Post

class PostTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.candidate1 = User.objects.create_user(
            username='candidate1',
            password='password',
            role=User.Role.CANDIDATE
        )
        self.candidate1_token = Token.objects.create(user=self.candidate1)

        self.candidate2 = User.objects.create_user(
            username='candidate2',
            password='password',
            role=User.Role.CANDIDATE
        )
        self.candidate2_token = Token.objects.create(user=self.candidate2)

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

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.post('/api/posts/', {'content': 'Candidate post'})
        self.candidate_post_id = response.data['id']

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.post('/api/posts/', {'content': 'Employer post'})
        self.employer_post_id = response.data['id']

    def test_candidate_can_create_post(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.post('/api/posts/', {'content': 'Hello world'})
        self.assertEqual(response.status_code, 201)

    def test_employer_can_create_post(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.post('/api/posts/', {'content': 'We are hiring!'})
        self.assertEqual(response.status_code, 201)

    def test_unauthenticated_user_cannot_create_post(self):
        self.client.credentials()
        response = self.client.post('/api/posts/', {'content': 'Hello world'})
        self.assertEqual(response.status_code, 401)

    def test_anyone_can_list_posts(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.get('/api/posts/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_candidate_can_update_own_post(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.patch(f'/api/posts/{self.candidate_post_id}/', {'content': 'Updated'})
        self.assertEqual(response.status_code, 200)

    def test_employer_can_update_own_post(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.patch(f'/api/posts/{self.employer_post_id}/', {'content': 'Updated'})
        self.assertEqual(response.status_code, 200)

    def test_candidate_cannot_update_employer_post(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.patch(f'/api/posts/{self.employer_post_id}/', {'content': 'Updated'})
        self.assertEqual(response.status_code, 403)

    def test_employer_cannot_update_candidate_post(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.patch(f'/api/posts/{self.candidate_post_id}/', {'content': 'Updated'})
        self.assertEqual(response.status_code, 403)

    def test_employer1_cannot_update_employer2_post(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer2_token.key)
        response = self.client.patch(f'/api/posts/{self.employer_post_id}/', {'content': 'Updated'})
        self.assertEqual(response.status_code, 403)

    def test_candidate_can_delete_own_post(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.delete(f'/api/posts/{self.candidate_post_id}/')
        self.assertEqual(response.status_code, 204)

    def test_employer_can_delete_own_post(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.delete(f'/api/posts/{self.employer_post_id}/')
        self.assertEqual(response.status_code, 204)

    def test_candidate_cannot_delete_employer_post(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.delete(f'/api/posts/{self.employer_post_id}/')
        self.assertEqual(response.status_code, 403)

    def test_employer_cannot_delete_candidate_post(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.delete(f'/api/posts/{self.candidate_post_id}/')
        self.assertEqual(response.status_code, 403)
