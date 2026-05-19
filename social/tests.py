from django.test import TestCase
from django.core.files.storage import default_storage
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from users.models import User, EmployerProfile
from .models import Post, PostImage, Comment, Like
import io
from shutil import rmtree
from PIL import Image

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

class CommentTests(TestCase):
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

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.post(f'/api/posts/{self.candidate_post_id}/comments/', {'content': 'Candidate comment'})
        self.candidate_comment_id = response.data['id']

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.post(f'/api/posts/{self.candidate_post_id}/comments/', {'content': 'Employer comment'})
        self.employer_comment_id = response.data['id']

    def test_candidate_can_comment_on_post(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.post(f'/api/posts/{self.candidate_post_id}/comments/', {'content': 'Hello'})
        self.assertEqual(response.status_code, 201)

    def test_employer_can_comment_on_post(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.post(f'/api/posts/{self.candidate_post_id}/comments/', {'content': 'Hello'})
        self.assertEqual(response.status_code, 201)

    def test_unauthenticated_user_cannot_comment(self):
        self.client.credentials()
        response = self.client.post(f'/api/posts/{self.candidate_post_id}/comments/', {'content': 'Hello'})
        self.assertEqual(response.status_code, 401)

    def test_user_can_list_comments(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.get(f'/api/posts/{self.candidate_post_id}/comments/')
        self.assertEqual(response.status_code, 200)

    def test_candidate_can_update_own_comment(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.patch(f'/api/posts/{self.candidate_post_id}/comments/{self.candidate_comment_id}/', {'content': 'Updated'})
        self.assertEqual(response.status_code, 200)

    def test_employer_can_update_own_comment(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.patch(f'/api/posts/{self.candidate_post_id}/comments/{self.employer_comment_id}/', {'content': 'Updated'})
        self.assertEqual(response.status_code, 200)

    def test_candidate_cannot_update_employer_comment(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.patch(f'/api/posts/{self.candidate_post_id}/comments/{self.employer_comment_id}/', {'content': 'Updated'})
        self.assertEqual(response.status_code, 403)

    def test_employer_cannot_update_candidate_comment(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.patch(f'/api/posts/{self.candidate_post_id}/comments/{self.candidate_comment_id}/', {'content': 'Updated'})
        self.assertEqual(response.status_code, 403)

    def test_candidate_can_delete_own_comment(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.delete(f'/api/posts/{self.candidate_post_id}/comments/{self.candidate_comment_id}/')
        self.assertEqual(response.status_code, 204)

    def test_employer_can_delete_own_comment(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.delete(f'/api/posts/{self.candidate_post_id}/comments/{self.employer_comment_id}/')
        self.assertEqual(response.status_code, 204)

    def test_candidate_cannot_delete_employer_comment(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.delete(f'/api/posts/{self.candidate_post_id}/comments/{self.employer_comment_id}/')
        self.assertEqual(response.status_code, 403)

    def test_employer_cannot_delete_candidate_comment(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.delete(f'/api/posts/{self.candidate_post_id}/comments/{self.candidate_comment_id}/')
        self.assertEqual(response.status_code, 403)

    def test_comment_on_nonexistent_post(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.post('/api/posts/9999/comments/', {'content': 'Hello'})
        self.assertEqual(response.status_code, 404)


class LikeTests(TestCase):
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

    def test_candidate_can_like_post(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.post(f'/api/posts/{self.candidate_post_id}/like/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['is_liked'])

    def test_employer_can_like_post(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.post(f'/api/posts/{self.candidate_post_id}/like/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['is_liked'])

    def test_candidate_can_toggle_like_off(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        self.client.post(f'/api/posts/{self.candidate_post_id}/like/')
        response = self.client.post(f'/api/posts/{self.candidate_post_id}/like/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['is_liked'])

    def test_employer_can_toggle_like_off(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        self.client.post(f'/api/posts/{self.candidate_post_id}/like/')
        response = self.client.post(f'/api/posts/{self.candidate_post_id}/like/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['is_liked'])

    def test_candidate_can_unlike_post(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        self.client.post(f'/api/posts/{self.candidate_post_id}/like/')
        response = self.client.post(f'/api/posts/{self.candidate_post_id}/like/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['is_liked'])

    def test_employer_can_unlike_post(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        self.client.post(f'/api/posts/{self.candidate_post_id}/like/')
        response = self.client.post(f'/api/posts/{self.candidate_post_id}/like/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['is_liked'])

    def test_unauthenticated_user_cannot_like_post(self):
        self.client.credentials()
        response = self.client.post(f'/api/posts/{self.candidate_post_id}/like/')
        self.assertEqual(response.status_code, 401)

    def test_like_nonexistent_post(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        response = self.client.post('/api/posts/9999/like/')
        self.assertEqual(response.status_code, 404)

    def test_likes_count_increases(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        self.client.post(f'/api/posts/{self.candidate_post_id}/like/')
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        self.client.post(f'/api/posts/{self.candidate_post_id}/like/')
        response = self.client.get(f'/api/posts/{self.candidate_post_id}/')
        self.assertEqual(response.data['likes_count'], 2)

    def test_likes_count_decreases_after_unlike(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        self.client.post(f'/api/posts/{self.candidate_post_id}/like/')
        self.client.post(f'/api/posts/{self.candidate_post_id}/like/')
        response = self.client.get(f'/api/posts/{self.candidate_post_id}/')
        self.assertEqual(response.data['likes_count'], 0)

    def test_employer_and_candidate_can_like_same_post(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        self.client.post(f'/api/posts/{self.employer_post_id}/like/')
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer2_token.key)
        self.client.post(f'/api/posts/{self.employer_post_id}/like/')
        response = self.client.get(f'/api/posts/{self.employer_post_id}/')
        self.assertEqual(response.data['likes_count'], 2)

class PostImageTests(TestCase):
    def setUp(self):
        # https://stackoverflow.com/questions/25792696/automatically-delete-media-root-between-tests
        rmtree(settings.MEDIA_ROOT, ignore_errors=True)

        self.client = APIClient()

        self.user1 = User.objects.create_user(
            username='user1',
            password='password',
            role=User.Role.CANDIDATE
        )
        self.user1_token = Token.objects.create(user=self.user1)

        self.user2 = User.objects.create_user(
            username='user2',
            password='password',
            role=User.Role.CANDIDATE
        )
        self.user2_token = Token.objects.create(user=self.user2)

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.post('/api/posts/', {'content': 'Test post'})
        self.post_id = response.data['id']

    def tearDown(self):
        # https://stackoverflow.com/questions/25792696/automatically-delete-media-root-between-tests
        rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def get_test_image(self, filename='test.png'):
        img = Image.new('RGB', (100, 100), color='red')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return SimpleUploadedFile(filename, buf.read(), content_type='image/png')

    def test_user_can_upload_image(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.post(
            f'/api/posts/{self.post_id}/images/',
            {'image': self.get_test_image()},
            format='multipart'
        )
        self.assertEqual(response.status_code, 201)

    def test_user_cannot_upload_image_to_other_users_post(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user2_token.key)
        response = self.client.post(
            f'/api/posts/{self.post_id}/images/',
            {'image': self.get_test_image()},
            format='multipart'
        )
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_user_cannot_upload_image(self):
        self.client.credentials()
        response = self.client.post(
            f'/api/posts/{self.post_id}/images/',
            {'image': self.get_test_image()},
            format='multipart'
        )
        self.assertEqual(response.status_code, 401)

    def test_user_can_list_images(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        self.client.post(
            f'/api/posts/{self.post_id}/images/',
            {'image': self.get_test_image()},
            format='multipart'
        )
        response = self.client.get(f'/api/posts/{self.post_id}/images/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_user_can_upload_multiple_images(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        self.client.post(
            f'/api/posts/{self.post_id}/images/',
            {'image': self.get_test_image()},
            format='multipart'
        )
        self.client.post(
            f'/api/posts/{self.post_id}/images/',
            {'image': self.get_test_image()},
            format='multipart'
        )
        response = self.client.get(f'/api/posts/{self.post_id}/images/')
        self.assertEqual(len(response.data), 2)

    def test_user_can_delete_image(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.post(
            f'/api/posts/{self.post_id}/images/',
            {'image': self.get_test_image()},
            format='multipart'
        )
        image_id = response.data['id']
        response = self.client.delete(f'/api/posts/{self.post_id}/images/{image_id}/')
        self.assertEqual(response.status_code, 204)

    def test_user_cannot_delete_other_users_image(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.post(
            f'/api/posts/{self.post_id}/images/',
            {'image': self.get_test_image()},
            format='multipart'
        )
        image_id = response.data['id']
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user2_token.key)
        response = self.client.delete(f'/api/posts/{self.post_id}/images/{image_id}/')
        self.assertEqual(response.status_code, 403)

    def test_user_can_replace_image(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.post(
            f'/api/posts/{self.post_id}/images/',
            {'image': self.get_test_image()},
            format='multipart'
        )
        image_id = response.data['id']
        response = self.client.patch(
            f'/api/posts/{self.post_id}/images/{image_id}/',
            {'image': self.get_test_image()},
            format='multipart'
        )
        self.assertEqual(response.status_code, 200)

    def test_user_cannot_replace_other_users_image(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.post(
            f'/api/posts/{self.post_id}/images/',
            {'image': self.get_test_image()},
            format='multipart'
        )
        image_id = response.data['id']
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user2_token.key)
        response = self.client.patch(
            f'/api/posts/{self.post_id}/images/{image_id}/',
            {'image': self.get_test_image()},
            format='multipart'
        )
        self.assertEqual(response.status_code, 403)

    def test_upload_to_nonexistent_post(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.post(
            '/api/posts/9999/images/',
            {'image': self.get_test_image()},
            format='multipart'
        )
        self.assertEqual(response.status_code, 404)

    def test_image_file_deleted_when_post_image_deleted(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.post(
            f'/api/posts/{self.post_id}/images/',
            {'image': self.get_test_image()},
            format='multipart'
        )
        image_id = response.data['id']
        image = PostImage.objects.get(pk=image_id)
        image_name = image.image.name

        self.client.delete(f'/api/posts/{self.post_id}/images/{image_id}/')
        self.assertFalse(default_storage.exists(image_name))

    def test_image_files_deleted_when_post_deleted(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response1 = self.client.post(
            f'/api/posts/{self.post_id}/images/',
            {'image': self.get_test_image()},
            format='multipart'
        )
        response2 = self.client.post(
            f'/api/posts/{self.post_id}/images/',
            {'image': self.get_test_image()},
            format='multipart'
        )
        image1_name = PostImage.objects.get(pk=response1.data['id']).image.name
        image2_name = PostImage.objects.get(pk=response2.data['id']).image.name

        self.client.delete(f'/api/posts/{self.post_id}/')

        self.assertFalse(default_storage.exists(image1_name))
        self.assertFalse(default_storage.exists(image2_name))

    def test_old_image_file_deleted_when_replaced(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.post(
            f'/api/posts/{self.post_id}/images/',
            {'image': self.get_test_image()},
            format='multipart'
        )
        image_id = response.data['id']
        old_image_name = PostImage.objects.get(pk=image_id).image.name

        self.client.patch(
            f'/api/posts/{self.post_id}/images/{image_id}/',
            {'image': self.get_test_image(filename='new_test.png')},
            format='multipart'
        )

        self.assertFalse(default_storage.exists(old_image_name))

    def test_new_image_file_exists_after_replace(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.post(
            f'/api/posts/{self.post_id}/images/',
            {'image': self.get_test_image()},
            format='multipart'
        )
        image_id = response.data['id']

        self.client.patch(
            f'/api/posts/{self.post_id}/images/{image_id}/',
            {'image': self.get_test_image()},
            format='multipart'
        )

        new_image_name = PostImage.objects.get(pk=image_id).image.name
        self.assertTrue(default_storage.exists(new_image_name))

    def test_images_count_in_post_response(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        self.client.post(
            f'/api/posts/{self.post_id}/images/',
            {'image': self.get_test_image()},
            format='multipart'
        )
        self.client.post(
            f'/api/posts/{self.post_id}/images/',
            {'image': self.get_test_image()},
            format='multipart'
        )
        response = self.client.get(f'/api/posts/{self.post_id}/')
        self.assertEqual(len(response.data['images']), 2)

    def test_images_empty_after_all_deleted(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.post(
            f'/api/posts/{self.post_id}/images/',
            {'image': self.get_test_image()},
            format='multipart'
        )
        image_id = response.data['id']
        self.client.delete(f'/api/posts/{self.post_id}/images/{image_id}/')
        response = self.client.get(f'/api/posts/{self.post_id}/images/')
        self.assertEqual(len(response.data), 0)

    def test_image_stored_in_correct_path(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user1_token.key)
        response = self.client.post(
            f'/api/posts/{self.post_id}/images/',
            {'image': self.get_test_image()},
            format='multipart'
        )
        image_id = response.data['id']
        image = PostImage.objects.get(pk=image_id)
        self.assertTrue(image.image.name.startswith(f'posts/{self.post_id}/'))


class PostCreateFieldTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='user1', password='password', role=User.Role.CANDIDATE)
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

    def test_create_post_without_content_returns_400(self):
        response = self.client.post('/api/posts/', {})
        self.assertEqual(response.status_code, 400)

    def test_create_post_response_contains_expected_fields(self):
        response = self.client.post('/api/posts/', {'content': 'Hello'})
        self.assertEqual(response.status_code, 201)
        for field in ('id', 'content', 'username', 'likes_count', 'comments_count', 'images', 'is_liked_by_me'):
            self.assertIn(field, response.data)

    def test_created_post_user_is_set_from_request(self):
        response = self.client.post('/api/posts/', {'content': 'Mine'})
        self.assertEqual(response.data['username'], self.user.username)

    def test_user_field_is_read_only_on_create(self):
        other = User.objects.create_user(username='other', password='password', role=User.Role.CANDIDATE)
        response = self.client.post('/api/posts/', {'content': 'Sneak', 'user': other.pk})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Post.objects.get(pk=response.data['id']).user, self.user)


class PostListFieldTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='user1', password='password', role=User.Role.CANDIDATE)
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        self.client.post('/api/posts/', {'content': 'First'})
        self.client.post('/api/posts/', {'content': 'Second'})

    def test_posts_ordered_newest_first(self):
        response = self.client.get('/api/posts/')
        self.assertEqual(response.data[0]['content'], 'Second')

    def test_list_includes_likes_count_comments_count_images(self):
        response = self.client.get('/api/posts/')
        for post in response.data:
            self.assertIn('likes_count', post)
            self.assertIn('comments_count', post)
            self.assertIn('images', post)

    def test_list_includes_is_liked_by_me(self):
        response = self.client.get('/api/posts/')
        for post in response.data:
            self.assertIn('is_liked_by_me', post)

    def test_unauthenticated_cannot_list_posts(self):
        self.client.credentials()
        response = self.client.get('/api/posts/')
        self.assertEqual(response.status_code, 401)


class PostDetailFieldTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='user1', password='password', role=User.Role.CANDIDATE,
            first_name='John', last_name='Doe'
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        response = self.client.post('/api/posts/', {'content': 'Hello'})
        self.post_id = response.data['id']

    def test_retrieve_nonexistent_post_returns_404(self):
        response = self.client.get('/api/posts/9999/')
        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_cannot_retrieve_post(self):
        self.client.credentials()
        response = self.client.get(f'/api/posts/{self.post_id}/')
        self.assertEqual(response.status_code, 401)

    def test_full_name_with_first_and_last_name(self):
        response = self.client.get(f'/api/posts/{self.post_id}/')
        self.assertEqual(response.data['full_name'], 'John Doe')

    def test_full_name_falls_back_to_username(self):
        user2 = User.objects.create_user(username='noname', password='password', role=User.Role.CANDIDATE)
        token2 = Token.objects.create(user=user2)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token2.key)
        r = self.client.post('/api/posts/', {'content': 'No name post'})
        response = self.client.get(f'/api/posts/{r.data["id"]}/')
        self.assertEqual(response.data['full_name'], 'noname')

    def test_deleted_post_no_longer_in_list(self):
        self.client.delete(f'/api/posts/{self.post_id}/')
        response = self.client.get('/api/posts/')
        ids = [p['id'] for p in response.data]
        self.assertNotIn(self.post_id, ids)

    def test_full_put_on_own_post(self):
        response = self.client.put(f'/api/posts/{self.post_id}/', {'content': 'Full update'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['content'], 'Full update')

    def test_update_nonexistent_post_returns_404(self):
        response = self.client.patch('/api/posts/9999/', {'content': 'X'})
        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_cannot_update_post(self):
        self.client.credentials()
        response = self.client.patch(f'/api/posts/{self.post_id}/', {'content': 'X'})
        self.assertEqual(response.status_code, 401)

    def test_unauthenticated_cannot_delete_post(self):
        self.client.credentials()
        response = self.client.delete(f'/api/posts/{self.post_id}/')
        self.assertEqual(response.status_code, 401)

    def test_delete_nonexistent_post_returns_404(self):
        response = self.client.delete('/api/posts/9999/')
        self.assertEqual(response.status_code, 404)

    def test_delete_removes_post_from_db(self):
        self.client.delete(f'/api/posts/{self.post_id}/')
        self.assertFalse(Post.objects.filter(pk=self.post_id).exists())


class CommentDetailTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(username='u1', password='password', role=User.Role.CANDIDATE)
        self.token1 = Token.objects.create(user=self.user1)
        self.user2 = User.objects.create_user(username='u2', password='password', role=User.Role.CANDIDATE)
        self.token2 = Token.objects.create(user=self.user2)

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token1.key)
        r = self.client.post('/api/posts/', {'content': 'Post'})
        self.post_id = r.data['id']

        r = self.client.post(f'/api/posts/{self.post_id}/comments/', {'content': 'User1 comment'})
        self.comment_id = r.data['id']

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token2.key)
        r2 = self.client.post('/api/posts/', {'content': 'Post2'})
        self.post2_id = r2.data['id']

    def test_retrieve_own_comment(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token1.key)
        response = self.client.get(f'/api/posts/{self.post_id}/comments/{self.comment_id}/')
        self.assertEqual(response.status_code, 200)

    def test_retrieve_nonexistent_comment_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token1.key)
        response = self.client.get(f'/api/posts/{self.post_id}/comments/9999/')
        self.assertEqual(response.status_code, 404)

    def test_comment_on_wrong_post_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token1.key)
        response = self.client.get(f'/api/posts/{self.post2_id}/comments/{self.comment_id}/')
        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_cannot_retrieve_comment(self):
        self.client.credentials()
        response = self.client.get(f'/api/posts/{self.post_id}/comments/{self.comment_id}/')
        self.assertEqual(response.status_code, 401)

    def test_unauthenticated_cannot_update_comment(self):
        self.client.credentials()
        response = self.client.patch(f'/api/posts/{self.post_id}/comments/{self.comment_id}/', {'content': 'X'})
        self.assertEqual(response.status_code, 401)

    def test_unauthenticated_cannot_delete_comment(self):
        self.client.credentials()
        response = self.client.delete(f'/api/posts/{self.post_id}/comments/{self.comment_id}/')
        self.assertEqual(response.status_code, 401)

    def test_create_comment_without_content_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token1.key)
        response = self.client.post(f'/api/posts/{self.post_id}/comments/', {})
        self.assertEqual(response.status_code, 400)

    def test_list_comments_on_nonexistent_post_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token1.key)
        response = self.client.get('/api/posts/9999/comments/')
        self.assertEqual(response.status_code, 404)

    def test_comments_ordered_oldest_first(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token1.key)
        self.client.post(f'/api/posts/{self.post_id}/comments/', {'content': 'Second'})
        response = self.client.get(f'/api/posts/{self.post_id}/comments/')
        self.assertEqual(response.data[0]['content'], 'User1 comment')

    def test_comments_count_increases_after_create(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token1.key)
        before = self.client.get(f'/api/posts/{self.post_id}/').data['comments_count']
        self.client.post(f'/api/posts/{self.post_id}/comments/', {'content': 'New'})
        after = self.client.get(f'/api/posts/{self.post_id}/').data['comments_count']
        self.assertEqual(after, before + 1)

    def test_comments_count_decreases_after_delete(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token1.key)
        before = self.client.get(f'/api/posts/{self.post_id}/').data['comments_count']
        self.client.delete(f'/api/posts/{self.post_id}/comments/{self.comment_id}/')
        after = self.client.get(f'/api/posts/{self.post_id}/').data['comments_count']
        self.assertEqual(after, before - 1)

    def test_comments_cascade_deleted_with_post(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token1.key)
        self.client.delete(f'/api/posts/{self.post_id}/')
        self.assertFalse(Comment.objects.filter(pk=self.comment_id).exists())

    def test_delete_removes_comment_from_db(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token1.key)
        self.client.delete(f'/api/posts/{self.post_id}/comments/{self.comment_id}/')
        self.assertFalse(Comment.objects.filter(pk=self.comment_id).exists())

    def test_comment_user_is_read_only(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token2.key)
        r = self.client.post(
            f'/api/posts/{self.post_id}/comments/',
            {'content': 'Legit', 'user': self.user1.pk, 'post': self.post2_id}
        )
        self.assertEqual(r.status_code, 201)
        comment = Comment.objects.get(pk=r.data['id'])
        self.assertEqual(comment.user, self.user2)
        self.assertEqual(comment.post_id, self.post_id)

    def test_full_name_in_comment_response(self):
        self.user1.first_name = 'Alice'
        self.user1.last_name = 'Smith'
        self.user1.save()
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token1.key)
        response = self.client.get(f'/api/posts/{self.post_id}/comments/{self.comment_id}/')
        self.assertEqual(response.data['full_name'], 'Alice Smith')

    def test_full_name_falls_back_to_username_in_comment(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token1.key)
        response = self.client.get(f'/api/posts/{self.post_id}/comments/{self.comment_id}/')
        self.assertEqual(response.data['full_name'], 'u1')


class LikeExtendedTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(username='u1', password='password', role=User.Role.CANDIDATE)
        self.token1 = Token.objects.create(user=self.user1)
        self.user2 = User.objects.create_user(username='u2', password='password', role=User.Role.CANDIDATE)
        self.token2 = Token.objects.create(user=self.user2)

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token1.key)
        r = self.client.post('/api/posts/', {'content': 'Post'})
        self.post_id = r.data['id']

    def test_like_response_contains_likes_count(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token1.key)
        response = self.client.post(f'/api/posts/{self.post_id}/like/')
        self.assertIn('likes_count', response.data)

    def test_is_liked_by_me_false_before_liking(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token1.key)
        response = self.client.get(f'/api/posts/{self.post_id}/')
        self.assertFalse(response.data['is_liked_by_me'])

    def test_is_liked_by_me_true_after_liking(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token1.key)
        self.client.post(f'/api/posts/{self.post_id}/like/')
        response = self.client.get(f'/api/posts/{self.post_id}/')
        self.assertTrue(response.data['is_liked_by_me'])

    def test_is_liked_by_me_false_after_unliking(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token1.key)
        self.client.post(f'/api/posts/{self.post_id}/like/')
        self.client.post(f'/api/posts/{self.post_id}/like/')
        response = self.client.get(f'/api/posts/{self.post_id}/')
        self.assertFalse(response.data['is_liked_by_me'])

    def test_is_liked_by_me_is_user_specific(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token1.key)
        self.client.post(f'/api/posts/{self.post_id}/like/')
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token2.key)
        response = self.client.get(f'/api/posts/{self.post_id}/')
        self.assertFalse(response.data['is_liked_by_me'])

    def test_db_never_has_duplicate_like(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token1.key)
        self.client.post(f'/api/posts/{self.post_id}/like/')
        count = Like.objects.filter(user=self.user1, post_id=self.post_id).count()
        self.assertLessEqual(count, 1)

    def test_likes_cascade_deleted_with_post(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token1.key)
        self.client.post(f'/api/posts/{self.post_id}/like/')
        self.client.delete(f'/api/posts/{self.post_id}/')
        self.assertFalse(Like.objects.filter(post_id=self.post_id).exists())


class LikeModelConstraintTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='u1', password='password', role=User.Role.CANDIDATE)
        self.user2 = User.objects.create_user(username='u2', password='password', role=User.Role.CANDIDATE)
        self.post = Post.objects.create(user=self.user1, content='Post')

    def test_unique_together_prevents_double_like(self):
        from django.db import IntegrityError
        Like.objects.create(user=self.user1, post=self.post)
        with self.assertRaises(IntegrityError):
            Like.objects.create(user=self.user1, post=self.post)

    def test_two_users_can_like_same_post(self):
        Like.objects.create(user=self.user1, post=self.post)
        Like.objects.create(user=self.user2, post=self.post)
        self.assertEqual(Like.objects.filter(post=self.post).count(), 2)

    def test_one_user_can_like_multiple_posts(self):
        post2 = Post.objects.create(user=self.user2, content='Post 2')
        Like.objects.create(user=self.user1, post=self.post)
        Like.objects.create(user=self.user1, post=post2)
        self.assertEqual(Like.objects.filter(user=self.user1).count(), 2)


class PostModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', password='password', role=User.Role.CANDIDATE)

    def test_created_at_set_automatically(self):
        post = Post.objects.create(user=self.user, content='Hello')
        self.assertIsNotNone(post.created_at)

    def test_updated_at_changes_on_save(self):
        post = Post.objects.create(user=self.user, content='v1')
        old = post.updated_at
        post.content = 'v2'
        post.save()
        post.refresh_from_db()
        self.assertGreaterEqual(post.updated_at, old)

    def test_deleting_post_cascades_to_comments(self):
        post = Post.objects.create(user=self.user, content='Bye')
        Comment.objects.create(post=post, user=self.user, content='A comment')
        post_id = post.pk
        post.delete()
        self.assertFalse(Comment.objects.filter(post_id=post_id).exists())

    def test_deleting_post_cascades_to_likes(self):
        post = Post.objects.create(user=self.user, content='Bye')
        Like.objects.create(post=post, user=self.user)
        post_id = post.pk
        post.delete()
        self.assertFalse(Like.objects.filter(post_id=post_id).exists())


class CommentModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', password='password', role=User.Role.CANDIDATE)
        self.post = Post.objects.create(user=self.user, content='A post')

    def test_created_at_set_automatically(self):
        comment = Comment.objects.create(post=self.post, user=self.user, content='Hi')
        self.assertIsNotNone(comment.created_at)

    def test_updated_at_changes_on_save(self):
        comment = Comment.objects.create(post=self.post, user=self.user, content='v1')
        old = comment.updated_at
        comment.content = 'v2'
        comment.save()
        comment.refresh_from_db()
        self.assertGreaterEqual(comment.updated_at, old)

    def test_multiple_comments_on_same_post(self):
        Comment.objects.create(post=self.post, user=self.user, content='A')
        Comment.objects.create(post=self.post, user=self.user, content='B')
        self.assertEqual(Comment.objects.filter(post=self.post).count(), 2)