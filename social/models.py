from django.db import models
from users.models import User

def post_image_upload_path(instance, filename):
    return f'posts/{instance.post.id}/{filename}'

# Post model
class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Needed for deleting a post's images when deleting the whole post
    def delete(self, *args, **kwargs):
        for image in self.images.all():
            image.image.delete(save=False)
        super().delete(*args, **kwargs)

class PostImage(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to=post_image_upload_path)
    created_at = models.DateTimeField(auto_now_add=True)

    # Needed for deleting the old image when replacing it with a new one
    def delete(self, *args, **kwargs):
        self.image.delete(save=False)
        super().delete(*args, **kwargs)

# Likes and comments model
# Note: Maybe we can add followers too?
class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Like(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    # Prevent duplicate likes in a post by the same user
    class Meta:
        unique_together = (('user', 'post'),)
