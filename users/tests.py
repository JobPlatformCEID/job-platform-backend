from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from .models import User, CandidateProfile, EmployerProfile

class UserTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.candidate = User.objects.create_user(
            username='candidate1',
            password='password',
            role=User.Role.CANDIDATE
        )
        CandidateProfile.objects.create(user=self.candidate)
        self.candidate_token = Token.objects.create(user=self.candidate)

        self.employer = User.objects.create_user(
            username='employer1',
            password='password',
            role=User.Role.EMPLOYER
        )
        EmployerProfile.objects.create(user=self.employer, company_name='Test Co')
        self.employer_token = Token.objects.create(user=self.employer)

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

    def test_login(self):
        response = self.client.post('/api/auth/login/', {
            'username': 'candidate1',
            'password': 'password'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.data)
        self.assertIn('role', response.data)

    def test_login_wrong_password(self):
        response = self.client.post('/api/auth/login/', {
            'username': 'candidate1',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 401)

    def test_get_candidate_profile(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.get('/api/candidates/me/')
        self.assertEqual(response.status_code, 200)

    def test_get_employer_profile(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer_token.key)
        response = self.client.get('/api/employers/me/')
        self.assertEqual(response.status_code, 200)

    def test_employer_cannot_access_candidate_profile(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer_token.key)
        response = self.client.get('/api/candidates/me/')
        self.assertEqual(response.status_code, 403)

    def test_candidate_cannot_access_employer_profile(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.get('/api/employers/me/')
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_cannot_access_profile(self):
        response = self.client.get('/api/candidates/me/')
        self.assertEqual(response.status_code, 401)

    def test_candidate_can_update_profile(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.put('/api/candidates/me/', {
            'phone': '1234567890',
            'location': 'Athens',
            'bio': 'Hello',
            'score': 0
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['location'], 'Athens')

    def test_employer_can_update_profile(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer_token.key)
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

    def test_login_returns_correct_role(self):
        response = self.client.post('/api/auth/login/', {
            'username': 'candidate1',
            'password': 'password'
        })
        self.assertEqual(response.data['role'], 'candidate')

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
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer_token.key)
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
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        self.client.put('/api/candidates/me/', {
            'phone': '123',
            'location': 'Athens',
            'bio': 'test',
            'score': 999
        })
        profile = CandidateProfile.objects.get(user=self.candidate)
        self.assertNotEqual(profile.score, 999)
    
    def test_login_nonexistent_user(self):
        response = self.client.post('/api/auth/login/', {
            'username': 'doesnotexist',
            'password': 'password'
        })
        self.assertEqual(response.status_code, 401)
 
    def test_candidate_partial_update(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.patch('/api/candidates/me/', {
            'location': 'Thessaloniki'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['location'], 'Thessaloniki')
 
    def test_employer_partial_update(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer_token.key)
        response = self.client.patch('/api/employers/me/', {
            'description': 'New description only'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['description'], 'New description only')
 
    def test_candidate_profile_default_score_is_zero(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.get('/api/candidates/me/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['score'], 0)
 
    def test_employer_cannot_update_candidate_profile(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer_token.key)
        response = self.client.put('/api/candidates/me/', {
            'location': 'Athens',
            'bio': 'Hacked'
        })
        self.assertEqual(response.status_code, 403)

    def test_get_current_user(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.get('/api/users/me/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('avatar', response.data)
        self.assertIn('first_name', response.data)
        self.assertIn('email', response.data)

    def test_get_public_user(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.get(f'/api/users/{self.employer.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('profile_id', response.data)
        self.assertIn('avatar', response.data)

    def test_unauthenticated_cannot_get_user(self):
        response = self.client.get(f'/api/users/{self.candidate.id}/')
        self.assertEqual(response.status_code, 401)

    def test_user_can_update_avatar(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.patch('/api/users/me/', {
            'first_name': 'John',
            'last_name': 'Doe',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['first_name'], 'John')

    def test_logout_invalidates_token(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate_token.key)
        response = self.client.post('/api/auth/logout/')
        self.assertEqual(response.status_code, 204)

        # Token should no longer work
        response = self.client.get('/api/candidates/me/')
        self.assertEqual(response.status_code, 401)

    def test_logout_requires_authentication(self):
        self.client.credentials()
        response = self.client.post('/api/auth/logout/')
        self.assertEqual(response.status_code, 401)

    def test_cannot_use_token_after_logout(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer_token.key)
        self.client.post('/api/auth/logout/')

        # Try to access a protected endpoint
        response = self.client.get('/api/employers/me/')
        self.assertEqual(response.status_code, 401)
