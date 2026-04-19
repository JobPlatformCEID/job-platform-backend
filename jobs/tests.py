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

    def test_candidate_can_view_own_applications(self):
        # Apply first
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        self.client.post(f'/api/jobs/{self.job_id}/apply/')

        # Then fetch applications
        response = self.client.get('/api/jobs/applications/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_candidate_cannot_see_other_candidates_applications(self):
        # candidate1 applies
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        self.client.post(f'/api/jobs/{self.job_id}/apply/')

        # candidate2 fetches — should see 0
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate2_token.key)
        response = self.client.get('/api/jobs/applications/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_employer_still_sees_all_applications(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        self.client.post(f'/api/jobs/{self.job_id}/apply/')

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.get('/api/jobs/applications/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)


class JobPostingFilterTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.employer1 = User.objects.create_user(
            username='employer1', password='password', role=User.Role.EMPLOYER
        )
        ep.objects.create(user=self.employer1, company_name='Company One')
        self.employer1_token = Token.objects.create(user=self.employer1)

        self.candidate1 = User.objects.create_user(
            username='candidate1', password='password', role=User.Role.CANDIDATE
        )
        cp.objects.create(user=self.candidate1)
        self.candidate1_token = Token.objects.create(user=self.candidate1)

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)

        self.job1 = JobPosting.objects.create(
            employer=self.employer1.employer_profile,
            title='Senior Python Developer',
            description='desc',
            requirements='degree',
            salary_min=50000, salary_max=80000,
            location='Athens',
            is_remote=False,
            contract_type='full_time',
            is_active=True,
        )
        self.job2 = JobPosting.objects.create(
            employer=self.employer1.employer_profile,
            title='Frontend Developer',
            description='desc',
            requirements='experience',
            salary_min=30000, salary_max=50000,
            location='Thessaloniki',
            is_remote=True,
            contract_type='part_time',
            is_active=True,
        )
        self.job3 = JobPosting.objects.create(
            employer=self.employer1.employer_profile,
            title='Data Analyst',
            description='desc',
            salary_min=40000, salary_max=60000,
            location='Remote',
            is_remote=True,
            contract_type='freelance',
            is_active=False,
        )

    def test_filter_by_title(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.get('/api/jobs/', {'title': 'python'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Senior Python Developer')

    def test_filter_by_location(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.get('/api/jobs/', {'location': 'athens'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['location'], 'Athens')

    def test_filter_by_contract_type(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.get('/api/jobs/', {'contract_type': 'part_time'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['contract_type'], 'part_time')

    def test_filter_by_is_remote(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.get('/api/jobs/', {'is_remote': 'true'})
        self.assertEqual(response.status_code, 200)
        # only active remote jobs (job2 is active+remote, job3 is remote but inactive)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Frontend Developer')

    def test_filter_by_salary_min(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.get('/api/jobs/', {'salary_min': 45000})
        self.assertEqual(response.status_code, 200)
        # job1 salary_min=50000 >= 45000, job2 salary_min=30000 < 45000
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Senior Python Developer')

    def test_filter_by_salary_max(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.get('/api/jobs/', {'salary_max': 55000})
        self.assertEqual(response.status_code, 200)
        # job1 salary_max=80000 > 55000, job2 salary_max=50000 <= 55000
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Frontend Developer')

    def test_filter_by_is_active(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.get('/api/jobs/', {'is_active': 'false'})
        self.assertEqual(response.status_code, 200)
        # default queryset filters is_active=True, so even with is_active=false param,
        # the base queryset restricts to active only
        self.assertEqual(len(response.data), 0)

    def test_combined_filters(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.get('/api/jobs/', {
            'is_remote': 'true',
            'contract_type': 'part_time',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Frontend Developer')

    def test_no_match_filter(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.get('/api/jobs/', {'title': 'nonexistent'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)


class JobApplicationFilterTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.employer1 = User.objects.create_user(
            username='employer1', password='password', role=User.Role.EMPLOYER
        )
        ep.objects.create(user=self.employer1, company_name='Company One')
        self.employer1_token = Token.objects.create(user=self.employer1)

        self.candidate1 = User.objects.create_user(
            username='candidate1', password='password', role=User.Role.CANDIDATE
        )
        cp.objects.create(user=self.candidate1)
        self.candidate1_token = Token.objects.create(user=self.candidate1)

        self.candidate2 = User.objects.create_user(
            username='candidate2', password='password', role=User.Role.CANDIDATE
        )
        cp.objects.create(user=self.candidate2)
        self.candidate2_token = Token.objects.create(user=self.candidate2)

        self.job1 = JobPosting.objects.create(
            employer=self.employer1.employer_profile,
            title='Python Developer',
            description='desc',
            location='Athens',
            is_remote=False,
            contract_type='full_time',
        )
        self.job2 = JobPosting.objects.create(
            employer=self.employer1.employer_profile,
            title='Frontend Developer',
            description='desc',
            location='Thessaloniki',
            is_remote=True,
            contract_type='part_time',
        )

        self.app1 = JobApplication.objects.create(
            candidate=self.candidate1.candidate_profile,
            job=self.job1,
            status='pending',
        )
        self.app2 = JobApplication.objects.create(
            candidate=self.candidate1.candidate_profile,
            job=self.job2,
            status='accepted',
        )
        self.app3 = JobApplication.objects.create(
            candidate=self.candidate2.candidate_profile,
            job=self.job1,
            status='rejected',
        )

    def test_candidate_filter_by_status(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.get('/api/jobs/applications/', {'status': 'accepted'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['status'], 'accepted')

    def test_candidate_filter_by_job(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.get('/api/jobs/applications/', {'job': self.job1.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['job'], self.job1.id)

    def test_candidate_filter_by_job_title(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.get('/api/jobs/applications/', {'job_title': 'python'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['job_title'], 'Python Developer')

    def test_candidate_filter_by_job_contract_type(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.get('/api/jobs/applications/', {'job_contract_type': 'part_time'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['job_title'], 'Frontend Developer')

    def test_candidate_filter_by_job_location(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.get('/api/jobs/applications/', {'job_location': 'athens'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['job_title'], 'Python Developer')

    def test_candidate_filter_by_job_is_remote(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.get('/api/jobs/applications/', {'job_is_remote': 'true'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['job_title'], 'Frontend Developer')

    def test_employer_filter_by_status(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.get('/api/jobs/applications/', {'status': 'pending'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['status'], 'pending')

    def test_employer_filter_by_job(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.get('/api/jobs/applications/', {'job': self.job1.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
