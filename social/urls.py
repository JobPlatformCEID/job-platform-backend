from django.urls import path
from .views import PostListCreateView, PostDetailView, CommentListCreateView, CommentDetailView, LikeView

urlpatterns = [
    path('posts/', PostListCreateView.as_view()),
    path('posts/<int:pk>/', PostDetailView.as_view()),
    path('posts/<int:pk>/comments/', CommentListCreateView.as_view()),
    path('posts/<int:pk>/comments/<int:comment_pk>/', CommentDetailView.as_view()),
    path('posts/<int:pk>/like/', LikeView.as_view()),
]
