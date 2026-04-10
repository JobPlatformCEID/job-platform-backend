from django.urls import path
from .views import InterviewSessionListCreateView, InterviewSessionDetailView, MessageListCreateView

urlpatterns = [
    path('sessions/', InterviewSessionListCreateView.as_view(), name='session-list-create'),
    path('sessions/<int:pk>/', InterviewSessionDetailView.as_view(), name='session-detail'),
    path('sessions/<int:session_id>/messages/', MessageListCreateView.as_view(), name='message-list-create'),
]