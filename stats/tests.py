from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from users.models import User, EmployerProfile , CandidateProfile, Education, Skill
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

class TopSkillsTest(TestCase):
    def setUp(self):
        self.client = APIClient()

        for i in range(5):
            user = User.objects.create_user(username=f'dev{i}', password='pass', role='candidate')
            profile = CandidateProfile.objects.create(user=user)
            Skill.objects.create(candidate=profile, name='Python')
            Skill.objects.create(candidate=profile, name='Django')

        user = User.objects.create_user(username='rustdev', password='pass', role='candidate')
        profile = CandidateProfile.objects.create(user=user)
        Skill.objects.create(candidate=profile, name='Rust')

    def test_returns_top_skills(self):
        url = reverse('top-skills')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data[0]['skill'], 'Python')
        self.assertEqual(data[0]['count'], 5)
        self.assertEqual(data[1]['skill'], 'Django')
        self.assertLessEqual(len(data), 10)
class TopCompaniesByJobPostingsTest(TestCase):
    def setUp(self):
        self.client = APIClient()

        for i in range(3):
            user = User.objects.create_user(username=f'emp{i}', password='pass', role='employer')
            employer = EmployerProfile.objects.create(user=user, company_name=f'Company{i}')
            for j in range(i + 1):
                JobPosting.objects.create(employer=employer, title='Dev', contract_type='full_time', description='desc')

    def test_returns_top_companies(self):
        url = reverse('top-companies')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data[0]['company'], 'Company2')
        self.assertEqual(data[0]['count'], 3)
        self.assertLessEqual(len(data), 10)

class AvgSalaryByTitleTest(TestCase):
    def setUp(self):
        self.client = APIClient()

        user = User.objects.create_user(username='emp', password='pass', role='employer')
        self.employer = EmployerProfile.objects.create(user=user, company_name='Acme')

        JobPosting.objects.create(employer=self.employer, title='Software Engineer', contract_type='full_time', description='desc', salary_min=3000, salary_max=5000)
        JobPosting.objects.create(employer=self.employer, title='Software Engineer', contract_type='full_time', description='desc', salary_min=4000, salary_max=6000)
        JobPosting.objects.create(employer=self.employer, title='Data Scientist', contract_type='full_time', description='desc', salary_min=5000, salary_max=8000)

    def test_returns_avg_salary_by_title(self):
        url = reverse('avg-salary-by-title')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = {item['title']: item for item in response.json()}
        self.assertEqual(data['Software Engineer']['avg_min'], 3500.0)
        self.assertEqual(data['Software Engineer']['avg_max'], 5500.0)
        self.assertEqual(data['Data Scientist']['avg_min'], 5000.0)