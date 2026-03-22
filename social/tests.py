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
        self.assertEqual(response.status_code, 201)

    def test_employer_can_like_post(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        response = self.client.post(f'/api/posts/{self.candidate_post_id}/like/')
        self.assertEqual(response.status_code, 201)

    def test_candidate_cannot_like_post_twice(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        self.client.post(f'/api/posts/{self.candidate_post_id}/like/')
        response = self.client.post(f'/api/posts/{self.candidate_post_id}/like/')
        self.assertEqual(response.status_code, 400)

    def test_employer_cannot_like_post_twice(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        self.client.post(f'/api/posts/{self.candidate_post_id}/like/')
        response = self.client.post(f'/api/posts/{self.candidate_post_id}/like/')
        self.assertEqual(response.status_code, 400)

    def test_candidate_can_unlike_post(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.candidate1_token.key)
        self.client.post(f'/api/posts/{self.candidate_post_id}/like/')
        response = self.client.delete(f'/api/posts/{self.candidate_post_id}/like/')
        self.assertEqual(response.status_code, 200)

    def test_employer_can_unlike_post(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employer1_token.key)
        self.client.post(f'/api/posts/{self.candidate_post_id}/like/')
        response = self.client.delete(f'/api/posts/{self.candidate_post_id}/like/')
        self.assertEqual(response.status_code, 200)

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
        self.client.delete(f'/api/posts/{self.candidate_post_id}/like/')
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
