from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from users.models import User, EmployerProfile , CandidateProfile, Education
from jobs.models import JobPosting

class JobPostingsByTitleTest(TestCase):
    def setUp(self):
        self.client = APIClient()

        employer_user = User.objects.create_user(
            username='employer1', password='pass', role='employer'
        )
        self.employer = EmployerProfile.objects.create(
            user=employer_user, company_name='Acme'
        )

        JobPosting.objects.create(employer=self.employer, title='Software Engineer', contract_type='full_time', description='desc')
        JobPosting.objects.create(employer=self.employer, title='Software Engineer', contract_type='full_time', description='desc')
        JobPosting.objects.create(employer=self.employer, title='Data Scientist', contract_type='full_time', description='desc')

    def test_returns_grouped_by_title(self):
        url = reverse('jobs-by-title')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        titles = {item['title']: item['count'] for item in data}
        self.assertEqual(titles['Software Engineer'], 2)
        self.assertEqual(titles['Data Scientist'], 1)

class CandidatesByEducationLevelTest(TestCase):
    def setUp(self):
        self.client = APIClient()

        for i in range(3):
            user = User.objects.create_user(username=f'candidate{i}', password='pass', role='candidate')
            profile = CandidateProfile.objects.create(user=user)
            Education.objects.create(candidate=profile, institution='MIT', degree='CS', level='bachelor')

        user = User.objects.create_user(username='candidate_master', password='pass', role='candidate')
        profile = CandidateProfile.objects.create(user=user)
        Education.objects.create(candidate=profile, institution='MIT', degree='CS', level='master')

    def test_returns_grouped_by_education_level(self):
        url = reverse('candidates-by-education')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = {item['level']: item['count'] for item in response.json()}
        self.assertEqual(data['bachelor'], 3)
        self.assertEqual(data['master'], 1)