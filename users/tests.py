from django.test import TestCase
from rest_framework.test import APIClient, APITestCase
from rest_framework.authtoken.models import Token
from .models import (
    User, CandidateProfile, EmployerProfile,
    WorkExperience, Education, Skill, Certification, Project
)


class UserTests(APITestCase):

    def setUp(self):
        self.client = APIClient()

        self.candidate = User.objects.create_user(
            username='candidate1',
            password='password',
            role=User.Role.CANDIDATE
        )
        self.candidate_profile = CandidateProfile.objects.create(user=self.candidate)
        self.candidate_token = Token.objects.create(user=self.candidate)

        self.employer = User.objects.create_user(
            username='employer1',
            password='password',
            role=User.Role.EMPLOYER
        )
        self.employer_profile = EmployerProfile.objects.create(
            user=self.employer,
            company_name='Test Co'
        )
        self.employer_token = Token.objects.create(user=self.employer)

    def _auth_candidate(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.candidate_token.key}')

    def _auth_employer(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.employer_token.key}')

    def test_register_candidate(self):
        response = self.client.post('/api/auth/register/', {
            'username': 'newcandidate',
            'password': 'password',
            'role': 'candidate'
        })
        self.assertEqual(response.status_code, 201)

    def test_register_employer(self):
        response = self.client.post('/api/auth/register/', {
            'username': 'newemployer',
            'password': 'password',
            'role': 'employer'
        })
        self.assertEqual(response.status_code, 201)

    def test_login_success(self):
        response = self.client.post('/api/auth/login/', {
            'username': 'candidate1',
            'password': 'password'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.data)
        self.assertIn('role', response.data)
        self.assertEqual(response.data['role'], 'candidate')

    def test_login_wrong_password(self):
        response = self.client.post('/api/auth/login/', {
            'username': 'candidate1',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 401)

    def test_login_nonexistent_user(self):
        response = self.client.post('/api/auth/login/', {
            'username': 'doesnotexist',
            'password': 'password'
        })
        self.assertEqual(response.status_code, 401)

    def test_get_candidate_profile(self):
        self._auth_candidate()
        response = self.client.get('/api/candidates/me/')
        self.assertEqual(response.status_code, 200)

    def test_get_employer_profile(self):
        self._auth_employer()
        response = self.client.get('/api/employers/me/')
        self.assertEqual(response.status_code, 200)

    def test_employer_cannot_access_candidate_profile(self):
        self._auth_employer()
        response = self.client.get('/api/candidates/me/')
        self.assertEqual(response.status_code, 403)

    def test_candidate_cannot_access_employer_profile(self):
        self._auth_candidate()
        response = self.client.get('/api/employers/me/')
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_cannot_access_profile(self):
        response = self.client.get('/api/candidates/me/')
        self.assertEqual(response.status_code, 401)

    def test_candidate_can_update_profile(self):
        self._auth_candidate()
        response = self.client.put('/api/candidates/me/', {
            'phone': '1234567890',
            'location': 'Athens',
            'bio': 'Hello',
            'score': 0
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['location'], 'Athens')

    def test_employer_can_update_profile(self):
        self._auth_employer()
        response = self.client.put('/api/employers/me/', {
            'company_name': 'Updated Co',
            'description': 'We are updated',
            'location': 'Athens',
            'website': 'https://updated.com'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['company_name'], 'Updated Co')

    def test_duplicate_username_registration(self):
        response = self.client.post('/api/auth/register/', {
            'username': 'candidate1',
            'password': 'password',
            'role': 'candidate'
        })
        self.assertEqual(response.status_code, 400)

    def test_register_invalid_role(self):
        response = self.client.post('/api/auth/register/', {
            'username': 'newuser',
            'password': 'password',
            'role': 'admin'
        })
        self.assertEqual(response.status_code, 400)

    def test_register_missing_password(self):
        response = self.client.post('/api/auth/register/', {
            'username': 'newuser',
            'role': 'candidate'
        })
        self.assertEqual(response.status_code, 400)

    def test_register_missing_role(self):
        response = self.client.post('/api/auth/register/', {
            'username': 'newuser',
            'password': 'password'
        })
        self.assertEqual(response.status_code, 400)

    def test_candidate_profile_created_on_register(self):
        self.client.post('/api/auth/register/', {
            'username': 'newcandidate2',
            'password': 'password',
            'role': 'candidate'
        })
        user = User.objects.get(username='newcandidate2')
        self.assertTrue(CandidateProfile.objects.filter(user=user).exists())

    def test_employer_profile_created_on_register(self):
        self.client.post('/api/auth/register/', {
            'username': 'newemployer2',
            'password': 'password',
            'role': 'employer'
        })
        user = User.objects.get(username='newemployer2')
        self.assertTrue(EmployerProfile.objects.filter(user=user).exists())

    def test_update_profile_invalid_website(self):
        self._auth_employer()
        response = self.client.put('/api/employers/me/', {
            'company_name': 'Test Co',
            'website': 'not-a-valid-url'
        })
        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_cannot_update_profile(self):
        response = self.client.put('/api/candidates/me/', {
            'location': 'Athens'
        })
        self.assertEqual(response.status_code, 401)

    def test_invalid_token_returns_401(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token faketoken123')
        response = self.client.get('/api/candidates/me/')
        self.assertEqual(response.status_code, 401)

    def test_candidate_score_is_read_only(self):
        self._auth_candidate()
        self.client.put('/api/candidates/me/', {
            'phone': '123',
            'location': 'Athens',
            'bio': 'test',
            'score': 999
        })
        profile = CandidateProfile.objects.get(user=self.candidate)
        self.assertNotEqual(profile.score, 999)

    def test_candidate_partial_update(self):
        self._auth_candidate()
        response = self.client.patch('/api/candidates/me/', {
            'location': 'Thessaloniki'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['location'], 'Thessaloniki')

    def test_employer_partial_update(self):
        self._auth_employer()
        response = self.client.patch('/api/employers/me/', {
            'description': 'New description only'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['description'], 'New description only')

    def test_candidate_profile_default_score_is_zero(self):
        self._auth_candidate()
        response = self.client.get('/api/candidates/me/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['score'], 0)

    def test_employer_cannot_update_candidate_profile(self):
        self._auth_employer()
        response = self.client.put('/api/candidates/me/', {
            'location': 'Athens',
            'bio': 'Hacked'
        })
        self.assertEqual(response.status_code, 403)

    def test_work_experience_candidate_can_create(self):
        self._auth_candidate()
        payload = {
            'title': 'Software Engineer',
            'company': 'Google',
            'employment_type': 'full_time',
            'location': 'Athens',
            'start_date': '2021-01-01',
            'end_date': '2022-01-01',
            'description': 'Built things.',
        }
        response = self.client.post('/api/work-experience/', payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['title'], 'Software Engineer')

    def test_work_experience_candidate_can_list(self):
        self._auth_candidate()
        payload = {
            'title': 'Software Engineer',
            'company': 'Google',
            'employment_type': 'full_time',
            'location': 'Athens',
            'start_date': '2021-01-01',
            'end_date': '2022-01-01',
            'description': 'Built things.',
        }
        self.client.post('/api/work-experience/', payload)
        response = self.client.get('/api/work-experience/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_work_experience_candidate_can_update(self):
        self._auth_candidate()
        payload = {
            'title': 'Software Engineer',
            'company': 'Google',
            'employment_type': 'full_time',
            'location': 'Athens',
            'start_date': '2021-01-01',
            'end_date': '2022-01-01',
            'description': 'Built things.',
        }
        create = self.client.post('/api/work-experience/', payload)
        pk = create.data['id']
        response = self.client.patch(f'/api/work-experience/{pk}/', {'title': 'Senior Engineer'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['title'], 'Senior Engineer')

    def test_work_experience_candidate_can_delete(self):
        self._auth_candidate()
        payload = {
            'title': 'Software Engineer',
            'company': 'Google',
            'employment_type': 'full_time',
            'location': 'Athens',
            'start_date': '2021-01-01',
            'end_date': '2022-01-01',
            'description': 'Built things.',
        }
        create = self.client.post('/api/work-experience/', payload)
        pk = create.data['id']
        response = self.client.delete(f'/api/work-experience/{pk}/')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(WorkExperience.objects.count(), 0)

    def test_work_experience_employer_cannot_create(self):
        self._auth_employer()
        payload = {
            'title': 'Software Engineer',
            'company': 'Google',
            'employment_type': 'full_time',
            'location': 'Athens',
            'start_date': '2021-01-01',
            'end_date': '2022-01-01',
            'description': 'Built things.',
        }
        response = self.client.post('/api/work-experience/', payload)
        self.assertEqual(response.status_code, 403)

    def test_work_experience_end_date_before_start_date_rejected(self):
        self._auth_candidate()
        payload = {
            'title': 'Software Engineer',
            'company': 'Google',
            'employment_type': 'full_time',
            'location': 'Athens',
            'start_date': '2022-01-01',
            'end_date': '2021-01-01',
            'description': 'Built things.',
        }
        response = self.client.post('/api/work-experience/', payload)
        self.assertEqual(response.status_code, 400)

    def test_work_experience_candidate_only_sees_own(self):
        other = User.objects.create_user(
            username='other', password='password', role=User.Role.CANDIDATE
        )
        other_profile = CandidateProfile.objects.create(user=other)
        WorkExperience.objects.create(
            candidate=other_profile, title='Other Job', company='Other Co',
            start_date='2020-01-01'
        )
        self._auth_candidate()
        response = self.client.get('/api/work-experience/')
        self.assertEqual(len(response.data), 0)

    def test_education_candidate_can_add(self):
        self._auth_candidate()
        payload = {
            'institution': 'University of Athens',
            'degree': 'BSc Computer Science',
            'field_of_study': 'Computer Science',
            'level': 'bachelor',
            'graduation_date': '2020-06-01',
        }
        response = self.client.post('/api/education/', payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['institution'], 'University of Athens')

    def test_education_candidate_can_list(self):
        self._auth_candidate()
        payload = {
            'institution': 'University of Athens',
            'degree': 'BSc Computer Science',
            'field_of_study': 'Computer Science',
            'level': 'bachelor',
            'graduation_date': '2020-06-01',
        }
        self.client.post('/api/education/', payload)
        response = self.client.get('/api/education/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_education_candidate_can_update(self):
        self._auth_candidate()
        payload = {
            'institution': 'University of Athens',
            'degree': 'BSc Computer Science',
            'field_of_study': 'Computer Science',
            'level': 'bachelor',
            'graduation_date': '2020-06-01',
        }
        create = self.client.post('/api/education/', payload)
        pk = create.data['id']
        response = self.client.patch(f'/api/education/{pk}/', {'degree': 'MSc Computer Science'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['degree'], 'MSc Computer Science')

    def test_education_candidate_can_delete(self):
        self._auth_candidate()
        payload = {
            'institution': 'University of Athens',
            'degree': 'BSc Computer Science',
            'field_of_study': 'Computer Science',
            'level': 'bachelor',
            'graduation_date': '2020-06-01',
        }
        create = self.client.post('/api/education/', payload)
        pk = create.data['id']
        response = self.client.delete(f'/api/education/{pk}/')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Education.objects.count(), 0)

    def test_education_employer_cannot_add(self):
        self._auth_employer()
        payload = {
            'institution': 'University of Athens',
            'degree': 'BSc Computer Science',
            'field_of_study': 'Computer Science',
            'level': 'bachelor',
            'graduation_date': '2020-06-01',
        }
        response = self.client.post('/api/education/', payload)
        self.assertEqual(response.status_code, 403)

    def test_education_invalid_level_rejected(self):
        self._auth_candidate()
        payload = {
            'institution': 'University of Athens',
            'degree': 'BSc Computer Science',
            'field_of_study': 'Computer Science',
            'level': 'postdoc',
            'graduation_date': '2020-06-01',
        }
        response = self.client.post('/api/education/', payload)
        self.assertEqual(response.status_code, 400)

    def test_skill_candidate_can_add(self):
        self._auth_candidate()
        payload = {'name': 'Python', 'level': 'expert'}
        response = self.client.post('/api/skills/', payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['name'], 'Python')

    def test_skill_candidate_can_list(self):
        self._auth_candidate()
        payload = {'name': 'Python', 'level': 'expert'}
        self.client.post('/api/skills/', payload)
        response = self.client.get('/api/skills/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_skill_candidate_can_update(self):
        self._auth_candidate()
        payload = {'name': 'Python', 'level': 'expert'}
        create = self.client.post('/api/skills/', payload)
        pk = create.data['id']
        response = self.client.patch(f'/api/skills/{pk}/', {'level': 'intermediate'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['level'], 'intermediate')

    def test_skill_candidate_can_delete(self):
        self._auth_candidate()
        payload = {'name': 'Python', 'level': 'expert'}
        create = self.client.post('/api/skills/', payload)
        pk = create.data['id']
        response = self.client.delete(f'/api/skills/{pk}/')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Skill.objects.count(), 0)

    def test_skill_employer_cannot_add(self):
        self._auth_employer()
        payload = {'name': 'Python', 'level': 'expert'}
        response = self.client.post('/api/skills/', payload)
        self.assertEqual(response.status_code, 403)

    def test_skill_invalid_proficiency_level_rejected(self):
        self._auth_candidate()
        response = self.client.post('/api/skills/', {'name': 'Python', 'level': 'god'})
        self.assertEqual(response.status_code, 400)

    def test_certification_candidate_can_add(self):
        self._auth_candidate()
        payload = {
            'name': 'AWS Certified Developer',
            'issuing_org': 'Amazon Web Services',
            'issue_date': '2022-01-01',
            'expiry_date': '2025-01-01',
            'credential_id': 'AWS-12345',
            'credential_url': 'https://aws.amazon.com/verify/AWS-12345',
        }
        response = self.client.post('/api/certifications/', payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['name'], 'AWS Certified Developer')

    def test_certification_candidate_can_list(self):
        self._auth_candidate()
        payload = {
            'name': 'AWS Certified Developer',
            'issuing_org': 'Amazon Web Services',
            'issue_date': '2022-01-01',
            'expiry_date': '2025-01-01',
            'credential_id': 'AWS-12345',
            'credential_url': 'https://aws.amazon.com/verify/AWS-12345',
        }
        self.client.post('/api/certifications/', payload)
        response = self.client.get('/api/certifications/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_certification_candidate_can_update(self):
        self._auth_candidate()
        payload = {
            'name': 'AWS Certified Developer',
            'issuing_org': 'Amazon Web Services',
            'issue_date': '2022-01-01',
            'expiry_date': '2025-01-01',
            'credential_id': 'AWS-12345',
            'credential_url': 'https://aws.amazon.com/verify/AWS-12345',
        }
        create = self.client.post('/api/certifications/', payload)
        pk = create.data['id']
        response = self.client.patch(f'/api/certifications/{pk}/', {'credential_id': 'AWS-99999'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['credential_id'], 'AWS-99999')

    def test_certification_candidate_can_delete(self):
        self._auth_candidate()
        payload = {
            'name': 'AWS Certified Developer',
            'issuing_org': 'Amazon Web Services',
            'issue_date': '2022-01-01',
            'expiry_date': '2025-01-01',
            'credential_id': 'AWS-12345',
            'credential_url': 'https://aws.amazon.com/verify/AWS-12345',
        }
        create = self.client.post('/api/certifications/', payload)
        pk = create.data['id']
        response = self.client.delete(f'/api/certifications/{pk}/')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Certification.objects.count(), 0)

    def test_certification_employer_cannot_add(self):
        self._auth_employer()
        payload = {
            'name': 'AWS Certified Developer',
            'issuing_org': 'Amazon Web Services',
            'issue_date': '2022-01-01',
            'expiry_date': '2025-01-01',
            'credential_id': 'AWS-12345',
            'credential_url': 'https://aws.amazon.com/verify/AWS-12345',
        }
        response = self.client.post('/api/certifications/', payload)
        self.assertEqual(response.status_code, 403)

    def test_certification_expiry_before_issue_date_rejected(self):
        self._auth_candidate()
        payload = {
            'name': 'AWS Certified Developer',
            'issuing_org': 'Amazon Web Services',
            'issue_date': '2023-01-01',
            'expiry_date': '2022-01-01',
            'credential_id': 'AWS-12345',
            'credential_url': 'https://aws.amazon.com/verify/AWS-12345',
        }
        response = self.client.post('/api/certifications/', payload)
        self.assertEqual(response.status_code, 400)

    def test_project_candidate_can_add(self):
        self._auth_candidate()
        payload = {
            'type': 'project',
            'title': 'My Portfolio',
            'description': 'A personal portfolio website.',
            'url': 'https://myportfolio.com',
            'start_date': '2021-06-01',
            'end_date': '2021-09-01',
        }
        response = self.client.post('/api/projects/', payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['title'], 'My Portfolio')

    def test_project_candidate_can_list(self):
        self._auth_candidate()
        payload = {
            'type': 'project',
            'title': 'My Portfolio',
            'description': 'A personal portfolio website.',
            'url': 'https://myportfolio.com',
            'start_date': '2021-06-01',
            'end_date': '2021-09-01',
        }
        self.client.post('/api/projects/', payload)
        response = self.client.get('/api/projects/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_project_candidate_can_update(self):
        self._auth_candidate()
        payload = {
            'type': 'project',
            'title': 'My Portfolio',
            'description': 'A personal portfolio website.',
            'url': 'https://myportfolio.com',
            'start_date': '2021-06-01',
            'end_date': '2021-09-01',
        }
        create = self.client.post('/api/projects/', payload)
        pk = create.data['id']
        response = self.client.patch(f'/api/projects/{pk}/', {'title': 'Updated Portfolio'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['title'], 'Updated Portfolio')

    def test_project_candidate_can_delete(self):
        self._auth_candidate()
        payload = {
            'type': 'project',
            'title': 'My Portfolio',
            'description': 'A personal portfolio website.',
            'url': 'https://myportfolio.com',
            'start_date': '2021-06-01',
            'end_date': '2021-09-01',
        }
        create = self.client.post('/api/projects/', payload)
        pk = create.data['id']
        response = self.client.delete(f'/api/projects/{pk}/')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Project.objects.count(), 0)

    def test_project_employer_cannot_add(self):
        self._auth_employer()
        payload = {
            'type': 'project',
            'title': 'My Portfolio',
            'description': 'A personal portfolio website.',
            'url': 'https://myportfolio.com',
            'start_date': '2021-06-01',
            'end_date': '2021-09-01',
        }
        response = self.client.post('/api/projects/', payload)
        self.assertEqual(response.status_code, 403)
    
    def test_candidate_can_review_employer_if_worked_there(self):
        self._auth_candidate()
        WorkExperience.objects.create(
            candidate=self.candidate_profile,
            title='Software Engineer',
            company='Test Co',
            employment_type='full_time',
            start_date='2021-01-01',
            end_date='2022-01-01'
        )
        response = self.client.post(f'/api/reviews/{self.employer_profile.id}/', {
            'rating': 5,
            'title': 'Great place to work',
            'comment': 'I enjoyed my time here'
        })
        self.assertEqual(response.status_code, 201)

    def test_candidate_cannot_review_employer_without_work_experience(self):
        self._auth_candidate()
        response = self.client.post(f'/api/reviews/{self.employer_profile.id}/', {
            'rating': 5,
            'title': 'Great place to work',
            'comment': 'I enjoyed my time here'
        })
        self.assertEqual(response.status_code, 403)
        self.assertIn('worked at', response.data['detail'])

    def test_candidate_cannot_review_own_company(self):
        self._auth_candidate()
        employer_as_candidate = User.objects.create_user(
            username='employerascandidate',
            password='password',
            role=User.Role.CANDIDATE
        )
        candidate_profile = CandidateProfile.objects.create(user=employer_as_candidate)
        employer_profile = EmployerProfile.objects.create(
            user=employer_as_candidate,
            company_name='My Company'
        )
        WorkExperience.objects.create(
            candidate=candidate_profile,
            title='Owner',
            company='My Company',
            employment_type='full_time',
            start_date='2021-01-01'
        )
        token = Token.objects.create(user=employer_as_candidate)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        response = self.client.post(f'/api/reviews/{employer_profile.id}/', {
            'rating': 5,
            'title': 'Great',
            'comment': 'Test'
        })
        self.assertEqual(response.status_code, 403)
        self.assertIn('own company', response.data['detail'])

    def test_employer_cannot_review_other_employer(self):
        self._auth_employer()
        other_employer = User.objects.create_user(
            username='otheremployer',
            password='password',
            role=User.Role.EMPLOYER
        )
        other_employer_profile = EmployerProfile.objects.create(
            user=other_employer,
            company_name='Other Co'
        )
        response = self.client.post(f'/api/reviews/{other_employer_profile.id}/', {
            'rating': 5,
            'title': 'Great',
            'comment': 'Test'
        })
        self.assertEqual(response.status_code, 403)
        self.assertIn('Employers cannot review', response.data['detail'])

    def test_candidate_cannot_submit_multiple_reviews(self):
        self._auth_candidate()
        WorkExperience.objects.create(
            candidate=self.candidate_profile,
            title='Software Engineer',
            company='Test Co',
            employment_type='full_time',
            start_date='2021-01-01',
            end_date='2022-01-01'
        )
        self.client.post(f'/api/reviews/{self.employer_profile.id}/', {
            'rating': 5,
            'title': 'First review',
            'comment': 'Test'
        })
        response = self.client.post(f'/api/reviews/{self.employer_profile.id}/', {
            'rating': 4,
            'title': 'Second review',
            'comment': 'Test'
        })
        self.assertEqual(response.status_code, 403)
        self.assertIn('already reviewed', response.data['detail'])

    def test_candidate_cannot_review_nonexistent_employer(self):
        self._auth_candidate()
        WorkExperience.objects.create(
            candidate=self.candidate_profile,
            title='Software Engineer',
            company='Test Co',
            employment_type='full_time',
            start_date='2021-01-01',
            end_date='2022-01-01'
        )
        response = self.client.post('/api/reviews/99999/', {
            'rating': 5,
            'title': 'Great',
            'comment': 'Test'
        })
        self.assertEqual(response.status_code, 404)

    def test_candidate_can_list_employer_reviews(self):
        self._auth_candidate()
        WorkExperience.objects.create(
            candidate=self.candidate_profile,
            title='Software Engineer',
            company='Test Co',
            employment_type='full_time',
            start_date='2021-01-01',
            end_date='2022-01-01'
        )
        self.client.post(f'/api/reviews/{self.employer_profile.id}/', {
            'rating': 5,
            'title': 'Great place',
            'comment': 'Test'
        })
        response = self.client.get(f'/api/reviews/{self.employer_profile.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_unauthenticated_cannot_create_review(self):
        response = self.client.post(f'/api/reviews/{self.employer_profile.id}/', {
            'rating': 5,
            'title': 'Great',
            'comment': 'Test'
        })
        self.assertEqual(response.status_code, 401)