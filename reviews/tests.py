from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from users.models import User, EmployerProfile, CandidateProfile
from .models import Review

class ReviewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        #create 2 employers

        # create employer1 (create his profile and token too)

        self.employer1 = User.objects.create_user(
            username='1',
            password='password',
            role=User.Role.EMPLOYER
        )

        self.employer1_profile = EmployerProfile.objects.create(
            user=self.employer1,
            company_name='Company One'
        )

        self.employer1_token = Token.objects.create(user=self.employer1)

        #create employer 2

        self.employer2 = User.objects.create_user(
            username='2',
            password='password',
            role=User.Role.EMPLOYER
        )

        self.employer2_profile = EmployerProfile.objects.create(
            user=self.employer2,
            company_name='Company Two'
        )

        self.employer2_token = Token.objects.create(user=self.employer2)

        #create 3 candidates

        #create candidate 1
        self.candidate1 = User.objects.create_user(
            username='candidate1',
            password='password',
            role=User.Role.CANDIDATE
        )

        CandidateProfile.objects.create(user=self.candidate1)
        self.candidate1_token = Token.objects.create(user=self.candidate1)

        #create candidate 2
        self.candidate2 = User.objects.create_user(
            username='candidate2',
            password='password',
            role=User.Role.CANDIDATE
        )
        
        CandidateProfile.objects.create(user=self.candidate2)
        self.candidate2_token = Token.objects.create(user=self.candidate2)

        #create candidate 3
        self.candidate3 = User.objects.create_user(
            username='candidate3',
            password='password',
            role=User.Role.CANDIDATE
        )
        
        CandidateProfile.objects.create(user=self.candidate3)
        self.candidate3_token = Token.objects.create(user=self.candidate3)

        self.url = f'/api/reviews/{self.employer1_profile.id}/'

    def test_candidate_leave_review(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token '+self.candidate1_token.key)

        response = self.client.post(self.url , {
            'score' : 5,
            'content' : 'mid'
        })
        
        self.assertEqual(response.status_code,201)

    def test_cannot_review_own_company(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token '+self.employer1_token.key)

        response = self.client.post(self.url , {
            'score' : 2,
            'content' : 'amazing my opinion is not biased'
        })

        self.assertEqual(response.status_code , 403)

    def test_owner_can_edit_review(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token '+self.candidate1_token.key)

        response = self.client.post(self.url , {
            'score' : 5,
            'content' : 'mid'
        })

        review_id = response.data['id']

        response = self.client.patch(f'/api/reviews/{self.employer1_profile.id}/{review_id}/',{
            'score' : 1,
            'content': 'actually its just bad'
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['edited'])

    def test_others_cant_edit_review(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token '+self.candidate1_token.key)

        response = self.client.post(f'{self.url}',{
            'score' : 1,
            'content': 'actually its just bad'
        })

        review_id = response.data['id']

        self.client.credentials(HTTP_AUTHORIZATION='Token '+self.candidate2_token.key)

        response = self.client.patch(f'/api/reviews/{self.employer1_profile.id}/{review_id}/',{
            'score':'10',
            'content':'amazing'
        })

        self.assertEqual(response.status_code , 403)

    def test_owner_can_delete_review(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)

        response = self.client.post(self.url, {
            'score': 5, 
            'content': 'ok'
        })

        review_id = response.data['id']

        response = self.client.delete(f'/api/reviews/{self.employer1_profile.id}/{review_id}/')
        self.assertEqual(response.status_code, 204)

    def test_other_user_cannot_delete_review(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)

        response = self.client.post(self.url, {
            'score': 5, 
            'content': 'ok'
        })

        review_id = response.data['id']

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate2_token.key)
        response = self.client.delete(f'/api/reviews/{self.employer1_profile.id}/{review_id}/')

        self.assertEqual(response.status_code, 403)

    def test_employer_can_review_other_company(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer2_token.key)

        response = self.client.post(self.url, {
            'score': 3,
            'content': 'good competitor'
        })

        self.assertEqual(response.status_code, 201)

    def test_score_out_of_range(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)

        response = self.client.post(self.url, {
            'score': 400, 
            'content': 'test'
        })

        self.assertEqual(response.status_code, 400)
    
    def test_calculation_of_avg(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        self.client.post(self.url, {'score': 3, 'content': 'decent'})

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate2_token.key)
        self.client.post(self.url, {'score': 4, 'content': 'good'})

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate3_token.key)
        self.client.post(self.url, {'score': 5, 'content': 'excellent'})

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)

        scores = [r['score'] for r in response.data]
        avg = sum(scores) / len(scores)
        self.assertAlmostEqual(avg, 4.0)

    def test_fetch_single_review(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.post(self.url, {'score': 5, 'content': 'ok'})
        review_id = response.data['id']

        response = self.client.get(f'/api/reviews/{self.employer1_profile.id}/{review_id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['score'], 5)
        self.assertEqual(response.data['content'], 'ok')

    def test_non_existent_employer(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.post('/api/reviews/99999/', {'score': 5, 'content': 'ok'})
        self.assertEqual(response.status_code, 404)

    def test_non_existent_review(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.get(f'/api/reviews/{self.employer1_profile.id}/99999/')
        self.assertEqual(response.status_code, 404)

    def test_empty_content_is_accepted(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.post(self.url, {'score': 3})
        self.assertEqual(response.status_code, 201)

    def test_delete_and_re_review(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)

        # leave a review
        response = self.client.post(self.url, {'score': 3, 'content': 'ok'})
        review_id = response.data['id']
        self.assertEqual(response.status_code, 201)

        # delete it
        response = self.client.delete(f'/api/reviews/{self.employer1_profile.id}/{review_id}/')
        self.assertEqual(response.status_code, 204)

        # leave a new review
        response = self.client.post(self.url, {'score': 5, 'content': 'changed my mind'})
        self.assertEqual(response.status_code, 201)



