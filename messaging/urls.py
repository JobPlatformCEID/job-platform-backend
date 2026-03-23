from django.urls import path
from .views import ConversationListCreateView, MessageListView

urlpatterns = [
    path('conversations/', ConversationListCreateView.as_view()),
    path('conversations/<int:pk>/messages/', MessageListView.as_view()),
]
