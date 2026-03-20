from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from users.models import User, CandidateProfile as cp, EmployerProfile as ep
from .models import JobPosting, JobApplication

"""
code | meaning
200  | OK — request succeeded
201  | Created — something was successfully created
400  | Bad Request — invalid data sent
401  | Unauthorized — no token or invalid token
403  | Forbidden — authenticated but not allowed
404  | Not Found — resource doesn't exist
"""

class JobPostingTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # create employer1
        self.employer1 = User.objects.create_user(
            username='employer1',
            password='password',
            role=User.Role.EMPLOYER
        )

        ep.objects.create(user=self.employer1, company_name='Company One')
        self.employer1_token = Token.objects.create(user=self.employer1)

        # create employer2
        self.employer2 = User.objects.create_user(
            username='employer2',
            password='password',
            role=User.Role.EMPLOYER
        )

        ep.objects.create(user=self.employer2, company_name='Company Two')
        self.employer2_token = Token.objects.create(user=self.employer2)

        # create candidate1
        self.candidate1 = User.objects.create_user(
            username='candidate1',
            password='password',
            role=User.Role.CANDIDATE
        )

        cp.objects.create(user=self.candidate1)
        self.candidate1_token = Token.objects.create(user=self.candidate1)

        # create candidate2
        self.candidate2 = User.objects.create_user(
            username='candidate2',
            password='password',
            role=User.Role.CANDIDATE
        )

        cp.objects.create(user=self.candidate2)
        self.candidate2_token = Token.objects.create(user=self.candidate2)

        # create a job posting as employer1 to use in tests
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.post('/api/jobs/', {
            'title': 'developer',
            'description': 'desc',
            'requirements': 'degree, experience',
            'contract_type': 'full_time'
        })

        self.job_id = response.data['id']

    def test_employer_can_create_job(self):

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.post('/api/jobs/', {
            'title': 'designer',
            'description': 'desc',
            'contract_type': 'part_time'
        })

        self.assertEqual(response.status_code, 201)

    def test_candidate_cannot_create_job(self):

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.post('/api/jobs/', {
            'title': 'developer',
            'description': 'desc',
            'contract_type': 'part_time'
        })

        self.assertEqual(response.status_code, 403)

    def test_employer2_cannot_delete_employer1_job(self):

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer2_token.key)
        response = self.client.delete(f'/api/jobs/{self.job_id}/')

        self.assertEqual(response.status_code, 403)

    def test_employer2_cannot_update_employer1_job(self):

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer2_token.key)
        response = self.client.patch(f'/api/jobs/{self.job_id}/', {
            'is_active': False
        })

        self.assertEqual(response.status_code, 403)

    def test_employer1_can_delete_own_job(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.delete(f'/api/jobs/{self.job_id}/')

        self.assertEqual(response.status_code, 204)

    def test_candidate_can_apply_to_job(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.post(f'/api/jobs/{self.job_id}/apply/')

        self.assertEqual(response.status_code, 201)

    def test_candidate_cannot_apply_twice(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)

        # first application
        self.client.post(f'/api/jobs/{self.job_id}/apply/')

        # second application - should be blocked
        response = self.client.post(f'/api/jobs/{self.job_id}/apply/')

        self.assertEqual(response.status_code, 400) 