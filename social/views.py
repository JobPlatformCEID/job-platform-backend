from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from rest_framework.response import Response
from django.db import IntegrityError
from .models import Post, Comment, Like
from .serializers import PostSerializer, CommentSerializer, LikeSerializer

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
        try:
            Like.objects.create(user=request.user, post=post)
            return Response({'message': 'Post liked.'}, status=status.HTTP_201_CREATED)
        except IntegrityError:
            raise ValidationError('You have already liked this post.')

    def delete(self, request, pk):
        try:
            like = Like.objects.get(user=request.user, post_id=pk)
            like.delete()
            return Response({'message': 'Post unliked.'}, status=status.HTTP_200_OK)
        except Like.DoesNotExist:
            raise NotFound('You have not liked this post.')
