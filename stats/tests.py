from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from users.models import User, EmployerProfile , CandidateProfile, Education, Skill
from jobs.models import JobPosting , JobApplication
from django.utils import timezone
from datetime import timedelta

class AuthenticatedStatsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.test_user = User.objects.create_user(
            username='test_stats_user', password='testpass123', role='employer'
        )
        self.client.force_authenticate(user=self.test_user)

class JobPostingsByTitleTest(AuthenticatedStatsTest):
    def setUp(self):
        super().setUp()
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

class CandidatesByEducationLevelTest(AuthenticatedStatsTest):
    def setUp(self):
        super().setUp()
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

class TopSkillsTest(AuthenticatedStatsTest):
    def setUp(self):
        super().setUp()
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

class TopCompaniesByJobPostingsTest(AuthenticatedStatsTest):
    def setUp(self):
        super().setUp()
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

class AvgSalaryByTitleTest(AuthenticatedStatsTest):
    def setUp(self):
        super().setUp()
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

class JobPostingsOverTimeTest(AuthenticatedStatsTest):
    def setUp(self):
        super().setUp()
        user = User.objects.create_user(username='emp_time', password='pass', role='employer')
        self.employer = EmployerProfile.objects.create(user=user, company_name='TimeCo')

        today = timezone.now()
        yesterday = today - timedelta(days=1)

        j1 = JobPosting.objects.create(employer=self.employer, title='Software Engineer', contract_type='full_time', description='desc')
        j2 = JobPosting.objects.create(employer=self.employer, title='Software Engineer', contract_type='full_time', description='desc')
        j3 = JobPosting.objects.create(employer=self.employer, title='Software Engineer', contract_type='full_time', description='desc')

        # Force created_at to yesterday for j1
        JobPosting.objects.filter(pk=j1.pk).update(created_at=yesterday)

    def test_requires_title_param(self):
        url = reverse('jobs-over-time')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)

    def test_returns_postings_over_time(self):
        url = reverse('jobs-over-time')
        response = self.client.get(url, {'title': 'Software Engineer'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # should have 2 dates: yesterday (1 posting) and today (2 postings)
        self.assertEqual(len(data), 2)
        counts = [item['count'] for item in data]
        self.assertIn(1, counts)
        self.assertIn(2, counts)

    def test_case_insensitive_filter(self):
        url = reverse('jobs-over-time')
        response = self.client.get(url, {'title': 'software engineer'})
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.json()), 0)

class RemoteVsOnsiteTest(AuthenticatedStatsTest):
    def setUp(self):
        super().setUp()
        user = User.objects.create_user(username='emp_remote', password='pass', role='employer')
        employer = EmployerProfile.objects.create(user=user, company_name='RemoteCo')
        JobPosting.objects.create(employer=employer, title='Dev', contract_type='full_time', description='desc', is_remote=True)
        JobPosting.objects.create(employer=employer, title='Dev', contract_type='full_time', description='desc', is_remote=True)
        JobPosting.objects.create(employer=employer, title='Dev', contract_type='full_time', description='desc', is_remote=False)

    def test_remote_vs_onsite(self):
        response = self.client.get(reverse('remote-vs-onsite'))
        self.assertEqual(response.status_code, 200)
        data = {item['type']: item['count'] for item in response.json()}
        self.assertEqual(data['Remote'], 2)
        self.assertEqual(data['On-site'], 1)


class JobsByContractTypeTest(AuthenticatedStatsTest):
    def setUp(self):
        super().setUp()
        user = User.objects.create_user(username='emp_contract', password='pass', role='employer')
        employer = EmployerProfile.objects.create(user=user, company_name='ContractCo')
        JobPosting.objects.create(employer=employer, title='Dev', contract_type='full_time', description='desc')
        JobPosting.objects.create(employer=employer, title='Dev', contract_type='full_time', description='desc')
        JobPosting.objects.create(employer=employer, title='Dev', contract_type='internship', description='desc')

    def test_jobs_by_contract_type(self):
        response = self.client.get(reverse('jobs-by-contract-type'))
        self.assertEqual(response.status_code, 200)
        data = {item['contract_type']: item['count'] for item in response.json()}
        self.assertEqual(data['full_time'], 2)
        self.assertEqual(data['internship'], 1)


class AvgSalaryByContractTypeTest(AuthenticatedStatsTest):
    def setUp(self):
        super().setUp()
        user = User.objects.create_user(username='emp_sal_contract', password='pass', role='employer')
        employer = EmployerProfile.objects.create(user=user, company_name='SalaryCo')
        JobPosting.objects.create(employer=employer, title='Dev', contract_type='full_time', description='desc', salary_min=3000, salary_max=5000)
        JobPosting.objects.create(employer=employer, title='Dev', contract_type='full_time', description='desc', salary_min=4000, salary_max=6000)
        JobPosting.objects.create(employer=employer, title='Intern', contract_type='internship', description='desc', salary_min=500, salary_max=1000)

    def test_avg_salary_by_contract_type(self):
        response = self.client.get(reverse('avg-salary-by-contract-type'))
        self.assertEqual(response.status_code, 200)
        data = {item['contract_type']: item for item in response.json()}
        self.assertEqual(data['full_time']['avg_min'], 3500.0)
        self.assertEqual(data['full_time']['avg_max'], 5500.0)


class MostCompetitiveJobsTest(AuthenticatedStatsTest):
    def setUp(self):
        super().setUp()
        emp_user = User.objects.create_user(username='emp_competitive', password='pass', role='employer')
        employer = EmployerProfile.objects.create(user=emp_user, company_name='CompetitiveCo')
        self.job1 = JobPosting.objects.create(employer=employer, title='Hot Job', contract_type='full_time', description='desc')
        self.job2 = JobPosting.objects.create(employer=employer, title='Cold Job', contract_type='full_time', description='desc')

        for i in range(5):
            cand_user = User.objects.create_user(username=f'cand_comp{i}', password='pass', role='candidate')
            candidate = CandidateProfile.objects.create(user=cand_user)
            JobApplication.objects.create(candidate=candidate, job=self.job1, status='pending')

        cand_user = User.objects.create_user(username='cand_cold', password='pass', role='candidate')
        candidate = CandidateProfile.objects.create(user=cand_user)
        JobApplication.objects.create(candidate=candidate, job=self.job2, status='pending')

    def test_most_competitive_jobs(self):
        response = self.client.get(reverse('most-competitive-jobs'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data[0]['title'], 'Hot Job')
        self.assertEqual(data[0]['applications'], 5)


class SalaryRangeDistributionTest(AuthenticatedStatsTest):
    def setUp(self):
        super().setUp()
        user = User.objects.create_user(username='emp_hist', password='pass', role='employer')
        employer = EmployerProfile.objects.create(user=user, company_name='HistCo')

        for salary in [500, 1000, 1500, 2000, 2500, 3000, 4000]:
            JobPosting.objects.create(
                employer=employer, title='Dev',
                contract_type='full_time', description='desc',
                salary_min=salary
            )

    def test_all_jobs_accounted_for(self):
        response = self.client.get(reverse('salary-range-distribution'))
        total = sum(item['count'] for item in response.json())
        self.assertEqual(total, 7)

    def test_empty_when_no_salaries(self):
        JobPosting.objects.all().delete()
        response = self.client.get(reverse('salary-range-distribution'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

class FilterByTitleTest(AuthenticatedStatsTest):
    def setUp(self):
        super().setUp()
        # employer
        emp_user = User.objects.create_user(username='emp_filter', password='pass', role='employer')
        self.employer1 = EmployerProfile.objects.create(user=emp_user, company_name='FilterCo')
        emp_user2 = User.objects.create_user(username='emp_filter2', password='pass', role='employer')
        self.employer2 = EmployerProfile.objects.create(user=emp_user2, company_name='OtherCo')

        # two job titles
        self.swe_job = JobPosting.objects.create(employer=self.employer1, title='Software Engineer', contract_type='full_time', description='desc', salary_min=4000, salary_max=6000, is_remote=True)
        self.other_job = JobPosting.objects.create(employer=self.employer2, title='Accountant', contract_type='part_time', description='desc', salary_min=1000, salary_max=2000, is_remote=False)

        # candidate who applied to swe_job
        cand_user = User.objects.create_user(username='cand_filter', password='pass', role='candidate')
        self.candidate = CandidateProfile.objects.create(user=cand_user)
        Education.objects.create(candidate=self.candidate, institution='MIT', degree='CS', level='master')
        Skill.objects.create(candidate=self.candidate, name='Python')
        Skill.objects.create(candidate=self.candidate, name='Django')
        JobApplication.objects.create(candidate=self.candidate, job=self.swe_job, status='pending')

        # candidate who applied to other_job only
        cand_user2 = User.objects.create_user(username='cand_filter2', password='pass', role='candidate')
        self.candidate2 = CandidateProfile.objects.create(user=cand_user2)
        Education.objects.create(candidate=self.candidate2, institution='Harvard', degree='Finance', level='bachelor')
        Skill.objects.create(candidate=self.candidate2, name='Excel')
        JobApplication.objects.create(candidate=self.candidate2, job=self.other_job, status='pending')

    def test_candidates_by_education_filtered(self):
        response = self.client.get(reverse('candidates-by-education'), {'title': 'Software Engineer'})
        self.assertEqual(response.status_code, 200)
        data = {item['level']: item['count'] for item in response.json()}
        self.assertIn('master', data)
        # accountant candidate should be excluded
        self.assertNotIn('bachelor', data)

    def test_top_skills_filtered(self):
        response = self.client.get(reverse('top-skills'), {'title': 'Software Engineer'})
        self.assertEqual(response.status_code, 200)
        skills = [item['skill'] for item in response.json()]
        self.assertIn('Python', skills)
        self.assertIn('Django', skills)
        # accountant candidate skill excluded
        self.assertNotIn('Excel', skills)

    def test_top_companies_filtered(self):
        response = self.client.get(reverse('top-companies'), {'title': 'Software Engineer'})
        self.assertEqual(response.status_code, 200)
        companies = [item['company'] for item in response.json()]
        self.assertIn('FilterCo', companies)
        self.assertNotIn('OtherCo', companies)

    def test_remote_vs_onsite_filtered(self):
        response = self.client.get(reverse('remote-vs-onsite'), {'title': 'Software Engineer'})
        self.assertEqual(response.status_code, 200)
        data = {item['type']: item['count'] for item in response.json()}
        self.assertIn('Remote', data)
        self.assertNotIn('On-site', data)

    def test_jobs_by_contract_type_filtered(self):
        response = self.client.get(reverse('jobs-by-contract-type'), {'title': 'Software Engineer'})
        self.assertEqual(response.status_code, 200)
        data = {item['contract_type']: item['count'] for item in response.json()}
        self.assertIn('full_time', data)
        self.assertNotIn('part_time', data)

    def test_avg_salary_by_contract_type_filtered(self):
        response = self.client.get(reverse('avg-salary-by-contract-type'), {'title': 'Software Engineer'})
        self.assertEqual(response.status_code, 200)
        data = {item['contract_type']: item for item in response.json()}
        self.assertIn('full_time', data)
        self.assertNotIn('part_time', data)
        self.assertEqual(data['full_time']['avg_min'], 4000.0)

    def test_salary_range_distribution_filtered(self):
        response = self.client.get(reverse('salary-range-distribution'), {'title': 'Software Engineer'})
        self.assertEqual(response.status_code, 200)
        total = sum(item['count'] for item in response.json())
        # only the swe job
        self.assertEqual(total, 1)