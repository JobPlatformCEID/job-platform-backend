from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from rest_framework.response import Response
from core.utils import compress_image
from .models import Post, Comment, Like, PostImage
from .serializers import PostSerializer, PostImageSerializer, CommentSerializer, LikeSerializer

class PostListCreateView(generics.ListCreateAPIView):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Post.objects.all().order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]
    queryset = Post.objects.all()

    def update(self, request, *args, **kwargs):
        post = self.get_object()
        if post.user != request.user:
            raise PermissionDenied('You can only edit your own posts.')
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        post = self.get_object()
        if post.user != request.user:
            raise PermissionDenied('You can only delete your own posts.')
        return super().destroy(request, *args, **kwargs)

class PostImageDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PostImageSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        try:
            image = PostImage.objects.get(
                pk=self.kwargs.get('image_pk'),
                post_id=self.kwargs.get('pk')
            )
        except PostImage.DoesNotExist:
            raise NotFound('Image not found.')
        return image

    def update(self, request, *args, **kwargs):
        image = self.get_object()
        if image.post.user != request.user:
            raise PermissionDenied('You can only edit images on your own posts.')
        image.image.delete(save=False)
        image_file = request.FILES.get('image')
        if image_file:
            compressed = compress_image(image_file)
            if compressed:
                request.FILES['image'] = compressed
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        image = self.get_object()
        if image.post.user != request.user:
            raise PermissionDenied('You can only delete images on your own posts.')
        return super().destroy(request, *args, **kwargs)

class PostImageListCreateView(generics.ListCreateAPIView):
    serializer_class = PostImageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        post_id = self.kwargs.get('pk')
        if not Post.objects.filter(pk=post_id).exists():
            raise NotFound('Post not found.')
        return PostImage.objects.filter(post_id=post_id)

    def create(self, request, *args, **kwargs):
        try:
            post = Post.objects.get(pk=self.kwargs.get('pk'))
        except Post.DoesNotExist:
            raise NotFound('Post not found.')
        if post.user != request.user:
            raise PermissionDenied('You can only add images to your own posts.')
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        post = Post.objects.get(pk=self.kwargs.get('pk'))
        image_file = self.request.FILES.get('image')
        if image_file:
            compressed = compress_image(image_file)
            serializer.save(post=post, image=compressed or image_file)
            return
        serializer.save(post=post)

class CommentListCreateView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        post_id = self.kwargs.get('pk')
        if not Post.objects.filter(pk=post_id).exists():
            raise NotFound('Post not found.')
        return Comment.objects.filter(post_id=post_id).order_by('created_at')

    def perform_create(self, serializer):
        try:
            post = Post.objects.get(pk=self.kwargs.get('pk'))
        except Post.DoesNotExist:
            raise NotFound('Post not found.')
        serializer.save(user=self.request.user, post=post)

class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        try:
            comment = Comment.objects.get(
                pk=self.kwargs.get('comment_pk'),
                post_id=self.kwargs.get('pk')
            )
        except Comment.DoesNotExist:
            raise NotFound('Comment not found.')
        return comment

    def update(self, request, *args, **kwargs):
        comment = self.get_object()
        if comment.user != request.user:
            raise PermissionDenied('You can only edit your own comments.')
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        comment = self.get_object()
        if comment.user != request.user:
            raise PermissionDenied('You can only delete your own comments.')
        return super().destroy(request, *args, **kwargs)

class LikeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            post = Post.objects.get(pk=pk)
        except Post.DoesNotExist:
            raise NotFound('Post not found.')
        like = Like.objects.filter(user=request.user, post=post).first()
        if like:
            like.delete()
            is_liked = False
        else:
            Like.objects.create(user=request.user, post=post)
            is_liked = True
        return Response({
            'is_liked': is_liked,
            'likes_count': post.likes.count(),
        }, status=status.HTTP_200_OK)
